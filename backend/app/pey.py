"""Cliente del API de pey (https://docs.pey.mx). Es el único módulo que usa la API key."""

from dataclasses import dataclass
from decimal import Decimal

import httpx

ESPERA_CREAR_SEGUNDOS = 10.0
ESPERA_CONSULTA_SEGUNDOS = 4.0


class ErrorPey(Exception):
    """pey rechazó la solicitud o no respondió (spec 001, RF-010, RF-027)."""

    def __init__(self, estado: int, tipo: str, mensaje: str, request_id: str | None = None):
        super().__init__(f"pey {estado} {tipo}: {mensaje}")
        self.estado = estado
        self.tipo = tipo
        self.mensaje = mensaje
        self.request_id = request_id


@dataclass(frozen=True)
class QrPey:
    id: str  # IDC de Banxico; el webhook lo manda como codiQrId
    qr_string: str  # texto que se codifica en el QR
    qr_image: str | None  # PNG en base64, si se pidió


@dataclass(frozen=True)
class PagoPey:
    """Pago con estado PAID devuelto por la consulta (spec 001, RF-015, RF-018)."""

    id: str
    monto: Decimal
    monto_base: Decimal | None
    pagado_en: int | None


@dataclass(frozen=True)
class ResultadoConsulta:
    """Pagos nuevos, páginas pedidas y el requestId de la última (spec 001, RF-025, RF-039)."""

    pagos: list[PagoPey]
    paginas: int
    request_id: str | None


class ClientePey:
    """Habla con pey. La consulta espera 4 s y crear el QR espera 10 s (spec 001, QP-1)."""

    def __init__(self, base_url: str, api_key: str, http: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http or httpx.AsyncClient(timeout=ESPERA_CREAR_SEGUNDOS)

    async def cerrar(self) -> None:
        await self._http.aclose()

    async def _pedir(self, metodo: str, ruta: str, espera: float, **kwargs) -> dict:
        if not self._api_key:
            raise ErrorPey(0, "sin llave", "Falta PEY_API_KEY en backend/.env")
        try:
            respuesta = await self._http.request(
                metodo,
                f"{self._base_url}{ruta}",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
                timeout=espera,
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise ErrorPey(0, "sin conexión", f"No se pudo contactar a pey: {error!r}") from error

        try:
            cuerpo = respuesta.json()
        except ValueError:
            cuerpo = {}
        if respuesta.is_success:
            return cuerpo if isinstance(cuerpo, dict) else {}

        error = cuerpo.get("error") if isinstance(cuerpo, dict) else None
        if not isinstance(error, dict):
            # El autorizador (401/403) responde {"message": "..."} sin el sobre "error".
            mensaje = cuerpo.get("message") if isinstance(cuerpo, dict) else None
            error = {"message": mensaje or respuesta.text[:200]}
        raise ErrorPey(
            respuesta.status_code,
            _tipo_de_estado(respuesta.status_code),
            error.get("message") or "Error sin detalle",
            error.get("requestId"),
        )

    async def crear_qr(
        self,
        monto: Decimal,
        concepto: str,
        expiracion: int,
        num_ref: str,
        metadata: dict[str, str] | None = None,
        generar_imagen: bool = True,
    ) -> QrPey:
        """POST /codi/qr: crea un cobro CoDi y devuelve el contenido del QR (spec 001, RF-001)."""
        cuerpo = await self._pedir(
            "POST",
            "/codi/qr",
            ESPERA_CREAR_SEGUNDOS,
            json={
                "amount": float(monto),
                "concept": concepto,
                "expiration": expiracion,
                "numRef": num_ref,
                "generateImage": generar_imagen,
                "metadata": metadata or {},
            },
        )
        if not cuerpo.get("id") or not cuerpo.get("qrString"):
            raise ErrorPey(502, "error general", "pey no devolvió id ni qrString")
        return QrPey(cuerpo["id"], cuerpo["qrString"], cuerpo.get("qrImage"))

    async def transacciones_qr(self, codi_qr_id: str) -> list[dict]:
        """GET de una página, para el script de prueba con pey real (spec 001, RF-025)."""
        cuerpo = await self._pedir(
            "GET",
            f"/transaction/codi/qr/{codi_qr_id}",
            ESPERA_CONSULTA_SEGUNDOS,
        )
        return cuerpo.get("items") or []

    async def pagos_del_qr(self, codi_qr_id: str, vistas: set[str]) -> ResultadoConsulta:
        """Sigue las páginas solo mientras traigan transacciones nuevas y devuelve las PAID.

        Cubre spec 001, RF-015, RF-025 y QP-2. `vistas` no se modifica.
        """
        pagos: list[PagoPey] = []
        paginas = 0
        token: str | None = None
        request_id: str | None = None
        while True:
            cuerpo = await self._pedir(
                "GET",
                f"/transaction/codi/qr/{codi_qr_id}",
                ESPERA_CONSULTA_SEGUNDOS,
                params={"nextToken": token} if token else None,
            )
            paginas += 1
            if cuerpo.get("requestId"):
                request_id = str(cuerpo["requestId"])
            hay_nueva = False
            for item in cuerpo.get("items") or []:
                identificador = item.get("id")
                if not identificador or identificador in vistas:
                    continue
                hay_nueva = True
                if item.get("status") != "PAID":
                    continue
                pagos.append(_pago_de(item, str(identificador)))
            siguiente = cuerpo.get("nextToken")
            if not hay_nueva or not siguiente:
                break
            token = str(siguiente)
        return ResultadoConsulta(pagos, paginas, request_id)


def _tipo_de_estado(estado: int) -> str:
    if estado in (401, 403):
        return "llave rechazada"
    if estado == 503:
        return "mantenimiento"
    return "error general"


def _pago_de(item: dict, identificador: str) -> PagoPey:
    desglose = item.get("amountBreakdown")
    monto_base = None
    if isinstance(desglose, dict) and desglose.get("base") is not None:
        monto_base = Decimal(str(desglose["base"]))
    pagado_en = item.get("datePaid")
    return PagoPey(
        id=identificador,
        monto=Decimal(str(item.get("amount", "0"))),
        monto_base=monto_base,
        pagado_en=None if pagado_en is None else int(pagado_en),
    )
