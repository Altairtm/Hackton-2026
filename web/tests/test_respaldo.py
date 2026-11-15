"""ver_cobro contra el servidor simulado (spec 002, T013)."""

from __future__ import annotations

import json
import urllib.request

import pytest
from conftest import abrir
from playwright.sync_api import Page, Route
from servidor_simulado import ServidorSimulado


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
def test_ver_cobro_200_devuelve_el_cobro(pagina: Page, servidor: ServidorSimulado) -> None:
    """Un 200 devuelve el cobro guardado (spec 002, RF-030, RF-033)."""
    cobro = _guardar_cobro(servidor)
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async (id) => {
          const { ver_cobro } = await import("/js/servidor.js");
          return ver_cobro(id);
        }""",
        cobro["id"],
    )
    assert resultado["cobro"]["id"] == cobro["id"]
    assert resultado["cobro"]["monto"] == 25.5
    assert resultado["cobro"]["concepto"] == "Tacos"


@pytest.mark.only_browser("chromium")
def test_ver_cobro_404_dice_que_no_existe(pagina: Page, servidor: ServidorSimulado) -> None:
    """Un 404 se informa como cobro que no existe (spec 002, RF-056, RF-057)."""
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async () => {
          const { ver_cobro } = await import("/js/servidor.js");
          return ver_cobro("NoExiste123");
        }"""
    )
    assert resultado == {"no_existe": True}


@pytest.mark.only_browser("chromium")
def test_ver_cobro_con_fallo_de_red_dice_sin_conexion(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Si la consulta se corta, ver_cobro informa sin conexión (spec 002, RF-030, RF-033)."""
    cobro = _guardar_cobro(servidor)
    abrir(pagina, servidor)
    pagina.route("**/api/cobros/**", _abortar)
    resultado = pagina.evaluate(
        """async (id) => {
          const { ver_cobro } = await import("/js/servidor.js");
          return ver_cobro(id);
        }""",
        cobro["id"],
    )
    assert resultado == {"sin_conexion": True}
