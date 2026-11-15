"""Canal de avisos de un cobro. El tiempo lo marca el reloj inyectado (spec 001, RF-028)."""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator

from app.cobros import VENCIDO, Cobro
from app.eventos import Difusor
from app.reloj import Reloj
from app.respaldo import ConsultaDeRespaldo


def _evento(nombre: str, datos: dict) -> str:
    return f"event: {nombre}\ndata: {json.dumps(datos, ensure_ascii=False)}\n\n"


def _espera(cobro: Cobro, reloj: Reloj) -> float:
    ahora = reloj.ahora()
    falta_fin = cobro.fin_ventana - ahora
    espera = min(5.0, falta_fin)
    if ahora < cobro.expira_en:
        espera = min(espera, cobro.expira_en - ahora)
    return espera


async def _esperar_o_evento(cola: asyncio.Queue, segundos: float, reloj: Reloj) -> None:
    """Espera un aviso o que pasen `segundos` en el reloj, lo que ocurra primero."""
    if segundos <= 0 or not cola.empty():
        return
    lector = asyncio.create_task(cola.get())
    dormido = asyncio.create_task(reloj.dormir(segundos))
    try:
        hecho, _pendientes = await asyncio.wait(
            {lector, dormido}, return_when=asyncio.FIRST_COMPLETED
        )
        if lector in hecho and not lector.cancelled():
            cola.put_nowait(lector.result())
    finally:
        for tarea in (lector, dormido):
            if not tarea.done():
                tarea.cancel()
        for tarea in (lector, dormido):
            if tarea.cancelled() or not tarea.done():
                with contextlib.suppress(asyncio.CancelledError):
                    await tarea


def _sacar(cola: asyncio.Queue) -> tuple[str, dict] | None:
    if cola.empty():
        return None
    nombre, datos = cola.get_nowait()
    if nombre in ("pago", "cancelado"):
        return nombre, datos
    return None


async def flujo_de_avisos(
    cobro: Cobro,
    difusor: Difusor,
    consulta: ConsultaDeRespaldo,
    reloj: Reloj,
) -> AsyncIterator[str]:
    """Emite estado, pago, cancelado, vencido, fin y la señal de vida (spec 001, RF-030)."""
    cola = difusor.suscribir(cobro.id)
    try:
        yield "retry: 3000\n\n"
        yield _evento("estado", cobro.publico())
        if reloj.ahora() >= cobro.fin_ventana:
            yield _evento("fin", cobro.publico())
            return
        ultimo_envio = reloj.ahora()
        ya_vencido = False
        while reloj.ahora() < cobro.fin_ventana:
            pendiente = _sacar(cola)
            if pendiente is not None:
                yield _evento(*pendiente)
                ultimo_envio = reloj.ahora()
                continue
            await consulta.consultar(cobro, intervalo_minimo=5)
            pendiente = _sacar(cola)
            if pendiente is not None:
                yield _evento(*pendiente)
                ultimo_envio = reloj.ahora()
                continue
            if not ya_vencido and cobro.estado(reloj.ahora()) == VENCIDO:
                ya_vencido = True
                yield _evento("vencido", cobro.publico())
                ultimo_envio = reloj.ahora()
                continue
            if reloj.ahora() - ultimo_envio >= 15:
                yield ": sigo conectado\n\n"
                ultimo_envio = reloj.ahora()
                continue
            espera = _espera(cobro, reloj)
            if espera <= 0:
                break
            await _esperar_o_evento(cola, espera, reloj)
        if not ya_vencido and cobro.estado(reloj.ahora()) == VENCIDO:
            yield _evento("vencido", cobro.publico())
        yield _evento("fin", cobro.publico())
    finally:
        difusor.cancelar(cobro.id, cola)
