"""Arranque de la web: la marca y la política de seguridad (spec 002, RF-060, RF-077)."""

import http.client

from conftest import abrir
from playwright.sync_api import ConsoleMessage, Page, expect
from servidor_simulado import ServidorSimulado


def test_la_pagina_abre_y_muestra_pago_facil(pagina: Page, servidor: ServidorSimulado) -> None:
    """La marca se lee PAGO FÁCIL al abrir la página (spec 002, RF-060)."""
    abrir(pagina, servidor)
    expect(pagina.locator('[data-prueba="marca"]')).to_have_text("PAGO FÁCIL")


def test_la_pagina_carga_sin_errores_ni_bloqueos_de_la_politica(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """La carga no escribe errores ni dispara securitypolicyviolation (spec 002, RF-077)."""
    errores: list[str] = []

    def anotar(mensaje: ConsoleMessage) -> None:
        if mensaje.type == "error":
            errores.append(mensaje.text)

    pagina.on("console", anotar)
    pagina.add_init_script(
        """
        window.__violaciones = [];
        document.addEventListener("securitypolicyviolation", (evento) => {
          window.__violaciones.push(evento.violatedDirective || "");
        });
        """
    )
    abrir(pagina, servidor)
    violaciones = pagina.evaluate("() => window.__violaciones")
    assert errores == []
    assert violaciones == []


def test_el_servidor_simulado_no_sirve_los_archivos_de_las_pruebas(
    servidor: ServidorSimulado,
) -> None:
    """Ninguna ruta, ni con puntos, deja leer web/tests/ desde el simulado (spec 002, T005)."""
    rutas = (
        "/tests/conftest.py",
        "/js/../tests/conftest.py",
        "/./tests/conftest.py",
        "/js/%2e%2e/tests/conftest.py",
    )
    for ruta in rutas:
        conexion = http.client.HTTPConnection("127.0.0.1", servidor.puerto)
        try:
            conexion.request("GET", ruta)
            assert conexion.getresponse().status == 404, ruta
        finally:
            conexion.close()
