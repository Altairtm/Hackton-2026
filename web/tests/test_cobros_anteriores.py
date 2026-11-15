"""cancelar_cobro contra el servidor simulado (spec 002, T013)."""

from __future__ import annotations

import json
import urllib.request

import pytest
from conftest import abrir
from playwright.sync_api import Page, Route
from servidor_simulado import ServidorSimulado

_MENSAJE_SIN_CONEXION = "No hay conexión con el servidor. Revisa tu internet e intenta de nuevo."
_DETALLE_NO_EXISTE = "Ese cobro no existe"
_DETALLE_NO_CANCELA = "Solo se puede cancelar un cobro que todavía no se paga ni vence"


def _guardar_cobro(servidor: ServidorSimulado) -> dict[str, object]:
    """Crea un cobro en el simulado sin pasar por el módulo de la web."""
    cuerpo = json.dumps({"monto": 25.5, "concepto": "Tacos"}).encode()
    peticion = urllib.request.Request(
        f"{servidor.origen}/api/cobros",
        data=cuerpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(peticion) as respuesta:
        datos = json.load(respuesta)
    if not isinstance(datos, dict):
        raise AssertionError("el simulado no devolvió un cobro")
    return datos


def _abortar(ruta: Route) -> None:
    ruta.abort()


@pytest.mark.only_browser("chromium")
def test_cancelar_cobro_200_devuelve_el_cobro(pagina: Page, servidor: ServidorSimulado) -> None:
    """Cancelar pide POST …/cancelar y devuelve el cobro (spec 002, RF-047)."""
    cobro = _guardar_cobro(servidor)
    identificador = str(cobro["id"])
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async (id) => {
          const { cancelar_cobro } = await import("/js/servidor.js");
          return cancelar_cobro(id);
        }""",
        identificador,
    )
    ruta = f"/api/cobros/{identificador}/cancelar"
    assert ("POST", ruta, None) in servidor.peticiones
    assert resultado["cobro"]["id"] == identificador
    assert resultado["cobro"]["estado"] == "cancelado"


@pytest.mark.only_browser("chromium")
@pytest.mark.parametrize(
    ("codigo", "detalle"),
    [
        (404, _DETALLE_NO_EXISTE),
        (409, _DETALLE_NO_CANCELA),
    ],
)
def test_cancelar_cobro_rechazado_devuelve_el_detail(
    pagina: Page, servidor: ServidorSimulado, codigo: int, detalle: str
) -> None:
    """404 y 409 devuelven el detail del servidor (spec 002, RF-050)."""
    if codigo == 404:
        identificador = "NoExiste123"
    else:
        cobro = _guardar_cobro(servidor)
        identificador = str(cobro["id"])
        servidor.agregar_pago(identificador, 10)
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async (id) => {
          const { cancelar_cobro } = await import("/js/servidor.js");
          return cancelar_cobro(id);
        }""",
        identificador,
    )
    assert resultado == {"mensaje": detalle}


@pytest.mark.only_browser("chromium")
def test_cancelar_cobro_con_fallo_de_red_dice_sin_conexion(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Si cancelar se corta, el mensaje pide revisar la conexión (spec 002, RF-050)."""
    cobro = _guardar_cobro(servidor)
    abrir(pagina, servidor)
    pagina.route("**/api/cobros/**", _abortar)
    resultado = pagina.evaluate(
        """async (id) => {
          const { cancelar_cobro } = await import("/js/servidor.js");
          return cancelar_cobro(id);
        }""",
        cobro["id"],
    )
    assert resultado == {"mensaje": _MENSAJE_SIN_CONEXION}
