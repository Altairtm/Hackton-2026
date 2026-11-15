"""Consulta de respaldo y la puerta que registra un pago y lo avisa (spec 001, QP-7)."""

import logging
from decimal import Decimal

from app.cobros import Cobro, Pago, RepositorioCobros
from app.eventos import Difusor
from app.pey import ClientePey, ErrorPey
from app.reloj import Reloj

registro = logging.getLogger("pago_facil")


class ConsultaDeRespaldo:
    """Pregunta a pey por los pagos de un cobro y avisa los nuevos (spec 001, RF-025, RF-040)."""

    def __init__(
        self,
        cliente_pey: ClientePey,
        repositorio: RepositorioCobros,
        difusor: Difusor,
        reloj: Reloj,
    ) -> None:
        self._pey = cliente_pey
        self._repositorio = repositorio
        self._difusor = difusor
        self._reloj = reloj

    def registrar_y_avisar(
        self,
        cobro: Cobro,
        transaccion_id: str,
        monto_recibido: Decimal,
        monto_base: Decimal | None,
        pagado_en: int | None,
        fuente: str,
    ) -> Pago | None:
        """Registra el pago y, si es nuevo, publica el evento pago (spec 001, RF-014, RF-029)."""
        pago = self._repositorio.registrar_pago(
            cobro, transaccion_id, monto_recibido, monto_base, pagado_en, fuente
        )
        if pago is None:
            return None
        registro.info(
            "Pago cobro=%s transaccion=%s numero=%s fuente=%s",
            cobro.id,
            transaccion_id,
            pago.numero,
            fuente,
        )
        self._difusor.publicar(
            cobro.id,
            "pago",
            {"pago": pago.publico(), "cobro": cobro.publico()},
        )
        return pago

    async def consultar(self, cobro: Cobro, intervalo_minimo: float) -> None:
        """Consulta a pey si toca, y tolera sus fallas (spec 001, RF-025, RF-027, RF-039)."""
        ahora = self._reloj.ahora()
        if not cobro.en_ventana(ahora):
            return
        if ahora - cobro.ultima_consulta_pey < intervalo_minimo:
            return
        cobro.ultima_consulta_pey = ahora
        try:
            resultado = await self._pey.pagos_del_qr(cobro.codi_qr_id, self._repositorio.vistas)
        except ErrorPey as error:
            registro.warning(
                "No se pudo consultar el cobro %s en pey (requestId=%s)",
                cobro.id,
                error.request_id,
            )
            return
        nuevos = 0
        for pago_pey in resultado.pagos:
            if self.registrar_y_avisar(
                cobro,
                pago_pey.id,
                pago_pey.monto,
                pago_pey.monto_base,
                pago_pey.pagado_en,
                "consulta",
            ):
                nuevos += 1
        if resultado.request_id:
            registro.info(
                "Consulta cobro=%s paginas=%s pagos_nuevos=%s requestId=%s",
                cobro.id,
                resultado.paginas,
                nuevos,
                resultado.request_id,
            )
        else:
            registro.info(
                "Consulta cobro=%s paginas=%s pagos_nuevos=%s",
                cobro.id,
                resultado.paginas,
                nuevos,
            )
