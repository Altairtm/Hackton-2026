"""API de PAGO FÁCIL: crea cobros CoDi con pey y avisa a la web cuando se pagan."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from standardwebhooks.webhooks import Webhook, WebhookVerificationError

from app.cobros import PAGADO, PENDIENTE, VENCIDO, Cobro, RepositorioCobros
from app.config import Configuracion, obtener_configuracion
from app.eventos import Difusor, LimitePorIp
from app.pey import ClientePey, ErrorPey
from app.reloj import Reloj

registro = logging.getLogger("pago_facil")
_registro_listo = False

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


def configurar_registros() -> None:
    """Deja `pago_facil` en INFO con un manejador de consola (spec 001, RF-039)."""
    global _registro_listo
    registro.setLevel(logging.INFO)
    if _registro_listo:
        return
    consola = logging.StreamHandler()
    consola.setLevel(logging.INFO)
    consola.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    registro.addHandler(consola)
    _registro_listo = True
    registro.info("Registros de pago_facil activos")


def crear_app(
    config: Configuracion | None = None,
    cliente_pey: ClientePey | None = None,
    reloj: Reloj | None = None,
) -> FastAPI:
    """Crea la API con reloj, registros y el modelo de cobros (spec 001, RF-008, RF-039)."""
    config = config or obtener_configuracion()
    configurar_registros()
    reloj_de_la_app = reloj or Reloj()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        app.state.pey = cliente_pey or ClientePey(
            config.pey_api_base_url, config.pey_api_key.get_secret_value()
        )
        yield
        await app.state.pey.cerrar()

    app = FastAPI(title="PAGO FÁCIL", version="0.1.0", lifespan=ciclo_de_vida)
    app.state.reloj = reloj_de_la_app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.origenes_web,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    cobros = RepositorioCobros(reloj_de_la_app, config.gracia_segundos)
    difusor = Difusor()
    limite = LimitePorIp(config.limite_cobros_por_minuto)

    def buscar(cobro_id: str) -> Cobro:
        cobro = cobros.obtener(cobro_id)
        if cobro is None:
            raise HTTPException(404, "Ese cobro no existe")
        return cobro

    def registrar_pago(
        cobro: Cobro,
        transaccion_id: str,
        monto_recibido: Decimal,
        monto_base: Decimal | None,
        pagado_en: int | None,
        fuente: str,
    ) -> bool:
        """Pasa el pago por la única puerta y avisa si es nuevo. Mismo aviso `pagado` hasta F4."""
        pago = cobros.registrar_pago(
            cobro, transaccion_id, monto_recibido, monto_base, pagado_en, fuente
        )
        if pago is None:
            return False
        registro.info("Cobro %s pagado (transacción %s)", cobro.id, transaccion_id)
        difusor.publicar(cobro.id, PAGADO, cobro.publico())
        return True

    async def consultar_pago_en_pey(cobro: Cobro) -> None:
        """Respaldo del aviso: pregunta a pey si el QR ya tiene un pago (spec 001, RF-025)."""
        ahora = app.state.reloj.ahora()
        if ahora - cobro.ultima_consulta_pey < SEGUNDOS_ENTRE_CONSULTAS_A_PEY:
            return
        cobro.ultima_consulta_pey = ahora
        try:
            resultado = await app.state.pey.pagos_del_qr(cobro.codi_qr_id, cobros.vistas)
        except ErrorPey as error:
            registro.warning(
                "No se pudo consultar el cobro %s en pey: %s (requestId=%s)",
                cobro.id,
                error,
                error.request_id,
            )
            return
        for pago_pey in resultado.pagos:
            registrar_pago(
                cobro,
                pago_pey.id,
                pago_pey.monto,
                pago_pey.monto_base,
                pago_pey.pagado_en,
                "consulta",
            )
            return

    @app.get("/salud")
    async def salud() -> dict:
        return {
            "estado": "ok",
            "pey_api_key": bool(config.pey_api_key.get_secret_value()),
            "pey_webhook_secret": bool(config.pey_webhook_secret.get_secret_value()),
        }

    @app.exception_handler(RequestValidationError)
    async def errores_de_validacion(
        _solicitud: Request, _error: RequestValidationError
    ) -> JSONResponse:
        """Un texto en español en lugar de la lista de pydantic (spec 001, RF-004)."""
        return JSONResponse(
            status_code=422,
            content={"detail": "Los datos del cobro no son válidos."},
        )

    @app.post("/api/cobros", status_code=201)
    async def crear_cobro(solicitud: SolicitudCobro, request: Request) -> dict:
        if solicitud.monto > config.monto_maximo:
            raise HTTPException(422, f"El monto máximo de la demo es ${config.monto_maximo}")
        ip = request.client.host if request.client else "desconocida"
        if not limite.permitir(ip):
            raise HTTPException(429, "Demasiados cobros seguidos. Espera un minuto.")

        cobro = cobros.nuevo(
            solicitud.monto,
            solicitud.concepto,
            config.expiracion_segundos,
            ahora=app.state.reloj.ahora(),
        )
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
            if error.tipo == "sin llave":
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
        if cobro.estado(app.state.reloj.ahora()) == PENDIENTE:
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
                if cobro.estado(app.state.reloj.ahora()) == PAGADO:
                    yield mensaje(PAGADO, cobro.publico())
                    return
                while not await request.is_disconnected():
                    try:
                        evento, datos = await asyncio.wait_for(
                            cola.get(), timeout=SEGUNDOS_ENTRE_LATIDOS_SSE
                        )
                    except TimeoutError:
                        if cobro.estado(app.state.reloj.ahora()) == VENCIDO:
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
        if cobros.aviso_ya_visto(webhook_id):
            return {"recibido": True, "procesado": False}
        cobros.marcar_aviso(webhook_id)

        cobro = cobros.por_codi_qr(str(datos.get("codiQrId", "")))
        transaccion_id = datos.get("transactionId")
        if cobro is None or not transaccion_id:
            registro.warning("Webhook de un cobro desconocido: %s", datos.get("codiQrId"))
            return {"recibido": True, "procesado": False}
        try:
            monto = Decimal(str(datos.get("amount")))
        except InvalidOperation:
            raise HTTPException(400, "Monto no válido")

        procesado = registrar_pago(
            cobro, transaccion_id, monto, None, datos.get("datePaid"), "aviso"
        )
        return {"recibido": True, "procesado": procesado}

    return app


app = crear_app()
