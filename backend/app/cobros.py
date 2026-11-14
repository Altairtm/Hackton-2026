"""Cobros del MVP, guardados en memoria. La base de datos definitiva llega en el issue #23."""

import secrets
import time
from dataclasses import dataclass, field
from decimal import Decimal

PENDIENTE = "pendiente"
PAGADO = "pagado"
VENCIDO = "vencido"


@dataclass
class Cobro:
    id: str
    monto: Decimal
    concepto: str
    num_ref: str
    creado_en: int
    expira_en: int
    codi_qr_id: str = ""
    qr: str = ""
    qr_imagen: str | None = None
    pagado: bool = False
    pagado_en: int | None = None
    monto_pagado: Decimal | None = None
    transaccion_id: str | None = None
    ultima_consulta_pey: float = field(default=0.0, repr=False)

    @property
    def estado(self) -> str:
        if self.pagado:
            return PAGADO
        if time.time() > self.expira_en:
            return VENCIDO
        return PENDIENTE

    def publico(self) -> dict:
        """Lo que ve la web. Nunca incluye datos de la cuenta que recibe."""
        return {
            "id": self.id,
            "codiQrId": self.codi_qr_id,
            "monto": float(self.monto),
            "concepto": self.concepto,
            "estado": self.estado,
            "qr": self.qr,
            "qrImagen": self.qr_imagen,
            "creado_en": self.creado_en,
            "expira_en": self.expira_en,
            "pagado_en": self.pagado_en,
        }


class RepositorioCobros:
    def __init__(self) -> None:
        self._por_id: dict[str, Cobro] = {}
        self._por_codi_qr: dict[str, str] = {}
        self._transacciones: set[str] = set()

    def nuevo(self, monto: Decimal, concepto: str, expiracion: int) -> Cobro:
        ahora = int(time.time())
        cobro = Cobro(
            id=secrets.token_urlsafe(9),
            monto=monto,
            concepto=concepto,
            # Referencia numérica de hasta 7 dígitos, como pide CoDi.
            num_ref=str(secrets.randbelow(9_000_000) + 1_000_000),
            creado_en=ahora,
            expira_en=ahora + expiracion,
        )
        self._por_id[cobro.id] = cobro
        return cobro

    def vincular_qr(self, cobro: Cobro, codi_qr_id: str, qr: str, qr_imagen: str | None) -> None:
        cobro.codi_qr_id = codi_qr_id
        cobro.qr = qr
        cobro.qr_imagen = qr_imagen
        self._por_codi_qr[codi_qr_id] = cobro.id

    def descartar(self, cobro: Cobro) -> None:
        self._por_id.pop(cobro.id, None)

    def obtener(self, cobro_id: str) -> Cobro | None:
        return self._por_id.get(cobro_id)

    def por_codi_qr(self, codi_qr_id: str) -> Cobro | None:
        return self._por_id.get(self._por_codi_qr.get(codi_qr_id, ""))

    def marcar_pagado(
        self,
        cobro: Cobro,
        transaccion_id: str,
        monto_pagado: Decimal,
        pagado_en: int | None,
    ) -> bool:
        """Registra el pago. Devuelve False si esa transacción o ese cobro ya estaban pagados."""
        if transaccion_id in self._transacciones or cobro.pagado:
            self._transacciones.add(transaccion_id)
            return False
        self._transacciones.add(transaccion_id)
        cobro.pagado = True
        cobro.transaccion_id = transaccion_id
        cobro.monto_pagado = monto_pagado
        cobro.pagado_en = pagado_en or int(time.time())
        return True
