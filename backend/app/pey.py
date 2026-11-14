"""Cliente del API de pey (https://docs.pey.mx). Es el único módulo que usa la API key."""

from dataclasses import dataclass
from decimal import Decimal

import httpx


class ErrorPey(Exception):
    """pey rechazó la solicitud o no respondió."""

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


class ClientePey:
    def __init__(self, base_url: str, api_key: str, http: httpx.AsyncClient | None = None):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = http or httpx.AsyncClient(timeout=20)

    async def cerrar(self) -> None:
        await self._http.aclose()

    async def _pedir(self, metodo: str, ruta: str, **kwargs) -> dict:
        if not self._api_key:
            raise ErrorPey(0, "SIN_API_KEY", "Falta PEY_API_KEY en backend/.env")
        try:
            respuesta = await self._http.request(
                metodo,
                f"{self._base_url}{ruta}",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise ErrorPey(0, "SIN_CONEXION", f"No se pudo contactar a pey: {error!r}") from error

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
            error.get("type") or "ERROR_HTTP",
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
        """POST /codi/qr: crea un cobro CoDi y devuelve el contenido del QR."""
        cuerpo = await self._pedir(
            "POST",
            "/codi/qr",
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
            raise ErrorPey(502, "RESPUESTA_INESPERADA", "pey no devolvió id ni qrString")
        return QrPey(cuerpo["id"], cuerpo["qrString"], cuerpo.get("qrImage"))

    async def transacciones_qr(self, codi_qr_id: str) -> list[dict]:
        """GET /transaction/codi/qr/{id}: pagos de un QR. Respaldo si el webhook no llega."""
        cuerpo = await self._pedir("GET", f"/transaction/codi/qr/{codi_qr_id}")
        return cuerpo.get("items") or []
