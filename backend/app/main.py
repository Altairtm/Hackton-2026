"""API de PAGO FÁCIL: crea cobros CoDi con pey y avisa a la web cuando se pagan."""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from standardwebhooks.webhooks import Webhook, WebhookVerificationError

from app.cobros import PAGADO, PENDIENTE, VENCIDO, Cobro, RepositorioCobros
from app.config import Configuracion, obtener_configuracion
from app.eventos import Difusor, LimitePorIp
from app.pey import ClientePey, ErrorPey
from app.reloj import Reloj

registro = logging.getLogger("pago_facil")

EVENTO_QR_PAGADO = "codi.qr.payment_received"
SEGUNDOS_ENTRE_CONSULTAS_A_PEY = 3
SEGUNDOS_ENTRE_LATIDOS_SSE = 15


class SolicitudCobro(BaseModel):
    monto: Decimal = Field(gt=0, decimal_places=2, description="Monto en pesos mexicanos")
    concepto: str = Field(default="Cobro", max_length=40)

    @field_validator("concepto")
    @classmethod
    def limpiar_concepto(cls, valor: str) -> str:
        valor = " ".join(valor.split())
        if any(not c.isprintable() for c in valor):
            raise ValueError("El concepto tiene caracteres no válidos")
        return valor or "Cobro"


def crear_app(
    config: Configuracion | None = None,
    cliente_pey: ClientePey | None = None,
    reloj: Reloj | None = None,
) -> FastAPI:
    """Crea la API. Guarda el reloj y todavía no lo usa en la lógica (spec 001, principio V)."""
    config = config or obtener_configuracion()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        app.state.pey = cliente_pey or ClientePey(
            config.pey_api_base_url, config.pey_api_key.get_secret_value()
        )
        yield
        await app.state.pey.cerrar()

    app = FastAPI(title="PAGO FÁCIL", version="0.1.0", lifespan=ciclo_de_vida)
    app.state.reloj = reloj or Reloj()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origenes_web,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    cobros = RepositorioCobros()
    difusor = Difusor()
    limite = LimitePorIp(config.limite_cobros_por_minuto)
    webhooks_vistos: set[str] = set()

    def buscar(cobro_id: str) -> Cobro:
        cobro = cobros.obtener(cobro_id)
        if cobro is None:
            raise HTTPException(404, "Ese cobro no existe")
        return cobro

    def registrar_pago(
        cobro: Cobro, transaccion_id: str, monto: Decimal, pagado_en: int | None
    ) -> bool:
        if monto != cobro.monto:
            registro.warning("Cobro %s: se pidió %s y se pagó %s", cobro.id, cobro.monto, monto)
        if not cobros.marcar_pagado(cobro, transaccion_id, monto, pagado_en):
            return False
        registro.info("Cobro %s pagado (transacción %s)", cobro.id, transaccion_id)
        difusor.publicar(cobro.id, PAGADO, cobro.publico())
        return True

    async def consultar_pago_en_pey(cobro: Cobro) -> None:
        """Respaldo del webhook: pregunta a pey si el QR ya tiene un pago."""
        ahora = time.monotonic()
        if ahora - cobro.ultima_consulta_pey < SEGUNDOS_ENTRE_CONSULTAS_A_PEY:
            return
        cobro.ultima_consulta_pey = ahora
        try:
            transacciones = await app.state.pey.transacciones_qr(cobro.codi_qr_id)
        except ErrorPey as error:
            registro.warning("No se pudo consultar el cobro %s en pey: %s", cobro.id, error)
            return
        for transaccion in transacciones:
            if transaccion.get("status") == "PAID" and transaccion.get("id"):
                registrar_pago(
                    cobro,
                    transaccion["id"],
                    Decimal(str(transaccion.get("amount", cobro.monto))),
                    transaccion.get("datePaid"),
                )
                return

    @app.get("/salud")
    async def salud() -> dict:
        return {
            "estado": "ok",
            "pey_api_key": bool(config.pey_api_key.get_secret_value()),
            "pey_webhook_secret": bool(config.pey_webhook_secret.get_secret_value()),
        }

    @app.post("/api/cobros", status_code=201)
    async def crear_cobro(solicitud: SolicitudCobro, request: Request) -> dict:
        if solicitud.monto > config.monto_maximo:
            raise HTTPException(422, f"El monto máximo de la demo es ${config.monto_maximo}")
        ip = request.client.host if request.client else "desconocida"
        if not limite.permitir(ip):
            raise HTTPException(429, "Demasiados cobros seguidos. Espera un minuto.")

        cobro = cobros.nuevo(solicitud.monto, solicitud.concepto, config.expiracion_segundos)
        try:
            qr = await app.state.pey.crear_qr(
                monto=cobro.monto,
                concepto=cobro.concepto,
                expiracion=config.expiracion_segundos,
                num_ref=cobro.num_ref,
                metadata={"cobroId": cobro.id},
            )
        except ErrorPey as error:
            cobros.descartar(cobro)
            registro.error("pey no creó el cobro: %s (requestId=%s)", error, error.request_id)
            if error.tipo == "SIN_API_KEY":
                raise HTTPException(503, "El backend no tiene configurada la API key de pey")
            if error.estado in (401, 403):
                raise HTTPException(502, "pey rechazó la API key del backend")
            if error.estado == 503:
                raise HTTPException(503, "pey está en mantenimiento. Intenta de nuevo.")
            raise HTTPException(502, "No se pudo crear el cobro con pey. Intenta de nuevo.")

        cobros.vincular_qr(cobro, qr.id, qr.qr_string, qr.qr_image)
        return cobro.publico()

    @app.get("/api/cobros/{cobro_id}")
    async def ver_cobro(cobro_id: str) -> dict:
        cobro = buscar(cobro_id)
        if cobro.estado == PENDIENTE:
            await consultar_pago_en_pey(cobro)
        return cobro.publico()

    @app.get("/api/cobros/{cobro_id}/eventos")
    async def eventos_cobro(cobro_id: str, request: Request) -> StreamingResponse:
        cobro = buscar(cobro_id)

        def mensaje(evento: str, datos: dict) -> str:
            return f"event: {evento}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"

        async def flujo():
            cola = difusor.suscribir(cobro.id)
            try:
                yield "retry: 3000\n\n"
                if cobro.pagado:
                    yield mensaje(PAGADO, cobro.publico())
                    return
                while not await request.is_disconnected():
                    try:
                        evento, datos = await asyncio.wait_for(
                            cola.get(), timeout=SEGUNDOS_ENTRE_LATIDOS_SSE
                        )
                    except TimeoutError:
                        if cobro.estado == VENCIDO:
                            yield mensaje(VENCIDO, cobro.publico())
                            return
                        yield ": sigo conectado\n\n"
                        continue
                    yield mensaje(evento, datos)
                    if evento == PAGADO:
                        return
            finally:
                difusor.cancelar(cobro.id, cola)

        return StreamingResponse(
            flujo(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/webhooks/pey")
    async def webhook_pey(request: Request) -> dict:
        secreto = config.pey_webhook_secret.get_secret_value()
        if not secreto:
            raise HTTPException(503, "El webhook todavía no está configurado")
        cuerpo = await request.body()
        try:
            Webhook(secreto).verify(cuerpo, dict(request.headers))
        except WebhookVerificationError:
            raise HTTPException(401, "Firma de webhook no válida")

        try:
            datos = json.loads(cuerpo)
        except ValueError:
            raise HTTPException(400, "El cuerpo no es JSON")
        if not isinstance(datos, dict) or datos.get("type") != EVENTO_QR_PAGADO:
            return {"recibido": True, "procesado": False}

        webhook_id = request.headers.get("webhook-id", "")
        if webhook_id in webhooks_vistos:
            return {"recibido": True, "procesado": False}
        webhooks_vistos.add(webhook_id)

        cobro = cobros.por_codi_qr(str(datos.get("codiQrId", "")))
        transaccion_id = datos.get("transactionId")
        if cobro is None or not transaccion_id:
            registro.warning("Webhook de un cobro desconocido: %s", datos.get("codiQrId"))
            return {"recibido": True, "procesado": False}
        try:
            monto = Decimal(str(datos.get("amount")))
        except InvalidOperation:
            raise HTTPException(400, "Monto no válido")

        procesado = registrar_pago(cobro, transaccion_id, monto, datos.get("datePaid"))
        return {"recibido": True, "procesado": procesado}

    return app


app = crear_app()
