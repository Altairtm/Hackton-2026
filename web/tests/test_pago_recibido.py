"""Pagos avisados, sonido y pantalla encendida (spec 002, T012)."""

from __future__ import annotations

import pytest
from conftest import abrir, bloqueos, sonidos, vibraciones
from playwright.sync_api import Page
from servidor_simulado import ServidorSimulado


@pytest.mark.only_browser("chromium")
def test_avisados_devuelve_solo_los_pagos_con_numero_mayor_al_ultimo_avisado(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """nuevos entrega cada pago una sola vez, en orden (spec 002, RF-029)."""
    abrir(pagina, servidor)
    numeros = pagina.evaluate(
        """async () => {
          const { Avisados } = await import("/js/avisados.js");
          const avisados = new Avisados();
          const cobro = {
            id: "CobroAvisos01",
            numero_de_pagos: 2,
            pagos: [
              { numero: 1, monto_recibido: 25.5 },
              { numero: 2, monto_recibido: 10 },
            ],
          };
          const primera = avisados.nuevos(cobro).map((pago) => pago.numero);
          cobro.pagos.push({ numero: 3, monto_recibido: 1 });
          cobro.numero_de_pagos = 3;
          const segunda = avisados.nuevos(cobro).map((pago) => pago.numero);
          const tercera = avisados.nuevos(cobro).map((pago) => pago.numero);
          return { primera, segunda, tercera };
        }"""
    )
    assert numeros == {"primera": [1, 2], "segunda": [3], "tercera": []}


@pytest.mark.only_browser("chromium")
def test_avisados_lleva_la_cuenta_por_cobro(pagina: Page, servidor: ServidorSimulado) -> None:
    """El pago 1 de otro cobro sigue siendo nuevo (spec 002, RF-029)."""
    abrir(pagina, servidor)
    numeros = pagina.evaluate(
        """async () => {
          const { Avisados } = await import("/js/avisados.js");
          const avisados = new Avisados();
          avisados.nuevos({
            id: "CobroAvisos01",
            numero_de_pagos: 1,
            pagos: [{ numero: 1, monto_recibido: 25.5 }],
          });
          return avisados
            .nuevos({
              id: "CobroAvisos02",
              numero_de_pagos: 1,
              pagos: [{ numero: 1, monto_recibido: 8 }],
            })
            .map((pago) => pago.numero);
        }"""
    )
    assert numeros == [1]


@pytest.mark.only_browser("chromium")
def test_marcar_todos_marca_sin_devolver_pagos(pagina: Page, servidor: ServidorSimulado) -> None:
    """marcar_todos fija el último avisado y nuevos no devuelve nada (spec 002, RF-053, RF-075)."""
    abrir(pagina, servidor)
    numeros = pagina.evaluate(
        """async () => {
          const { Avisados } = await import("/js/avisados.js");
          const avisados = new Avisados();
          const cobro = {
            id: "CobroAvisos01",
            numero_de_pagos: 2,
            pagos: [
              { numero: 1, monto_recibido: 25.5 },
              { numero: 2, monto_recibido: 10 },
            ],
          };
          const devuelto = avisados.marcar_todos(cobro);
          return {
            devuelto: devuelto === undefined ? null : devuelto,
            despues: avisados.nuevos(cobro).map((pago) => pago.numero),
          };
        }"""
    )
    assert numeros["devuelto"] is None
    assert numeros["despues"] == []


def test_el_sonido_se_desbloquea_con_un_toque_y_despues_suena_sin_otro(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """desbloquear suena en silencio; sonar ya no pide otro toque (spec 002, RF-022, RF-025)."""
    abrir(pagina, servidor)
    reproducciones = pagina.evaluate(
        """async () => {
          const { desbloquear, sonar } = await import("/js/sonido.js");
          desbloquear();
          const silencio = window.__sonidos.map((sonido) => ({
            volume: sonido.volume,
            muted: sonido.muted,
            src: sonido.src,
          }));
          sonar();
          return silencio;
        }"""
    )
    assert reproducciones
    assert all(sonido["volume"] == 0 for sonido in reproducciones)
    assert all(str(sonido["src"]).startswith("blob:") for sonido in reproducciones)
    assert sonidos(pagina) == 1


def test_vibrar_solo_si_el_celular_puede(
    pagina: Page, servidor: ServidorSimulado, browser_name: str
) -> None:
    """En Chromium vibra 200-100-200; en WebKit no lanza error (spec 002, RF-024)."""
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { vibrar } = await import("/js/sonido.js");
          vibrar();
        }"""
    )
    if browser_name == "chromium":
        assert vibraciones(pagina) == [[200, 100, 200]]


def test_mantener_encendida_pide_y_suelta_el_bloqueo(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Pedir dos veces cuenta un bloqueo; soltar lo libera (spec 002, RF-058, RF-059)."""
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { mantener_encendida } = await import("/js/pantalla.js");
          await mantener_encendida(true);
          await mantener_encendida(true);
          await mantener_encendida(false);
        }"""
    )
    assert bloqueos(pagina) == {"pedidos": 1, "soltados": 1}


def test_soltar_mientras_se_pide_el_bloqueo_no_lo_deja_pegado(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Si se suelta con el pedido en vuelo, el bloqueo que llega se libera (spec 002, RF-059)."""
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { mantener_encendida } = await import("/js/pantalla.js");
          const pedir = navigator.wakeLock.request.bind(navigator.wakeLock);
          navigator.wakeLock.request = (tipo) =>
            new Promise((resolver) => {
              setTimeout(() => resolver(pedir(tipo)), 50);
            });
          const pedido = mantener_encendida(true);
          await mantener_encendida(false);
          await pedido;
        }"""
    )
    assert bloqueos(pagina) == {"pedidos": 1, "soltados": 1}


def test_al_volver_a_la_pagina_se_vuelve_a_pedir_el_bloqueo(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Al volver a verse la página se pide otra vez el bloqueo (spec 002, RF-058)."""
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { mantener_encendida } = await import("/js/pantalla.js");
          await mantener_encendida(true);
          document.dispatchEvent(new Event("visibilitychange"));
          await new Promise((resolver) => {
            setTimeout(resolver, 0);
          });
        }"""
    )
    assert bloqueos(pagina)["pedidos"] == 2


def test_sin_wake_lock_no_falla(pagina: Page, servidor: ServidorSimulado) -> None:
    """Sin navigator.wakeLock, mantener la pantalla no lanza error (spec 002, RF-058)."""
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { mantener_encendida } = await import("/js/pantalla.js");
          Object.defineProperty(navigator, "wakeLock", {
            configurable: true,
            value: undefined,
          });
          await mantener_encendida(true);
        }"""
    )
