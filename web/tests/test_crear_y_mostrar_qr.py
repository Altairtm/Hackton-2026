"""Cuenta regresiva y crear_cobro contra el servidor simulado (spec 002, T011)."""

from __future__ import annotations

import pytest
from conftest import abrir, reloj
from playwright.sync_api import Page, Route
from servidor_simulado import ServidorSimulado

_MENSAJE_SIN_CONEXION = "No hay conexión con el servidor. Revisa tu internet e intenta de nuevo."
_MENSAJE_SIN_QR = "No se pudo mostrar el QR. Intenta de nuevo."
_HORA = 1_700_000_000


def _abortar(ruta: Route) -> None:
    ruta.abort()


@pytest.mark.only_browser("chromium")
def test_la_cuenta_descuenta_el_desfase_con_el_servidor_en_la_funcion(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Con el celular adelantado, el restante sigue la vigencia del servidor (spec 002, RF-019)."""
    abrir(pagina, servidor)
    instante = _HORA
    resultado = pagina.evaluate(
        """async (instante) => {
          const { desfase, restante } = await import("/js/cuenta.js");
          const cobro = { expira_en: instante + 600, hora_servidor: instante };
          const ahora = instante + 300;
          const diferencia = desfase(cobro, ahora);
          return { desfase: diferencia, restante: restante(cobro, diferencia, ahora) };
        }""",
        instante,
    )
    assert resultado == {"desfase": -300, "restante": 600}


@pytest.mark.only_browser("chromium")
def test_si_crear_tardo_9_segundos_la_cuenta_arranca_en_9_51_en_la_funcion(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Si el cobro tardó 9 s, al recibirlo quedan 9:51 (spec 002, RF-019)."""
    abrir(pagina, servidor)
    instante = _HORA
    texto = pagina.evaluate(
        """async (instante) => {
          const { desfase, restante, formato } = await import("/js/cuenta.js");
          const cobro = {
            creado_en: instante,
            expira_en: instante + 600,
            hora_servidor: instante + 9,
          };
          const ahora = instante + 9;
          const diferencia = desfase(cobro, ahora);
          return formato(restante(cobro, diferencia, ahora));
        }""",
        instante,
    )
    assert texto == "9:51"


@pytest.mark.only_browser("chromium")
def test_el_formato_de_la_cuenta_es_minutos_y_segundos(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """El formato es m:ss, trunca y no baja de 0:00 (spec 002, RF-018)."""
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async () => {
          const { formato } = await import("/js/cuenta.js");
          return {
            diez: formato(600),
            truncado: formato(591.7),
            menos_de_un_minuto: formato(59),
            cero: formato(0),
            negativo: formato(-5),
          };
        }"""
    )
    assert resultado == {
        "diez": "10:00",
        "truncado": "9:51",
        "menos_de_un_minuto": "0:59",
        "cero": "0:00",
        "negativo": "0:00",
    }


@pytest.mark.only_browser("chromium")
def test_sin_hora_del_servidor_se_usa_el_reloj_del_celular_y_se_avisa(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Sin hora_servidor el desfase es 0 y queda un aviso en consola (spec 002, RF-019)."""
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async () => {
          const avisos = [];
          const avisar = console.warn.bind(console);
          console.warn = (...partes) => {
            avisos.push(partes.join(" "));
            avisar(...partes);
          };
          const { desfase } = await import("/js/cuenta.js");
          return { desfase: desfase({ expira_en: 1000 }, 1000), avisos };
        }"""
    )
    assert resultado["desfase"] == 0
    assert any("hora_servidor" in texto for texto in resultado["avisos"])


@pytest.mark.only_browser("chromium")
def test_crear_cobro_manda_el_monto_como_numero_y_el_concepto(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """El cuerpo es monto numérico y concepto, en /api/cobros (spec 002, RF-009)."""
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { crear_cobro } = await import("/js/servidor.js");
          return crear_cobro(25.5, "Tacos");
        }"""
    )
    posts = [item for item in servidor.peticiones if item[0] == "POST"]
    assert ("POST", "/api/cobros", {"monto": 25.5, "concepto": "Tacos"}) in posts


@pytest.mark.only_browser("chromium")
def test_crear_cobro_201_con_imagen_devuelve_el_cobro(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Un 201 con imagen devuelve el cobro (spec 002, RF-009, RF-015)."""
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async () => {
          const { crear_cobro } = await import("/js/servidor.js");
          return crear_cobro(25.5, "Tacos");
        }"""
    )
    assert "mensaje" not in resultado
    cobro = resultado["cobro"]
    assert cobro["monto"] == 25.5
    assert cobro["concepto"] == "Tacos"
    assert isinstance(cobro["qr_imagen"], str) and cobro["qr_imagen"]
    assert isinstance(cobro["id"], str) and len(cobro["id"]) == 12


@pytest.mark.only_browser("chromium")
def test_crear_cobro_201_sin_imagen_devuelve_el_mensaje_del_qr(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Un 201 con qr_imagen null devuelve el mensaje del QR (spec 002, RF-078)."""
    servidor.responder_crear(cuerpo={"monto": 25.5, "concepto": "Tacos", "qr_imagen": None})
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async () => {
          const { crear_cobro } = await import("/js/servidor.js");
          return crear_cobro(25.5, "Tacos");
        }"""
    )
    assert resultado == {"mensaje": _MENSAJE_SIN_QR}


@pytest.mark.only_browser("chromium")
@pytest.mark.parametrize("codigo", [422, 429, 502, 503])
def test_crear_cobro_rechazado_devuelve_el_detail(
    pagina: Page, servidor: ServidorSimulado, codigo: int
) -> None:
    """422, 429, 502 y 503 devuelven el detail tal cual (spec 002, RF-012)."""
    detalle = f"detalle {codigo}"
    servidor.responder_crear(codigo=codigo, cuerpo={"detail": detalle})
    abrir(pagina, servidor)
    resultado = pagina.evaluate(
        """async () => {
          const { crear_cobro } = await import("/js/servidor.js");
          return crear_cobro(25.5, "Tacos");
        }"""
    )
    assert resultado == {"mensaje": detalle}


@pytest.mark.only_browser("chromium")
def test_crear_cobro_sin_respuesta_en_15_segundos_devuelve_sin_conexion(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """A los 14 s sigue esperando; a los 15 s avisa sin conexión (spec 002, RF-013)."""
    abrir(pagina, servidor)
    reloj(pagina, _HORA)
    servidor.responder_crear(sin_respuesta=True)
    pagina.evaluate(
        """() => {
          window.__listo = false;
          window.__resultado = null;
          return import("/js/servidor.js").then(({ crear_cobro }) => {
            crear_cobro(25.5, "Tacos").then((resultado) => {
              window.__resultado = resultado;
              window.__listo = true;
            });
          });
        }"""
    )
    pagina.clock.run_for(14_000)
    assert pagina.evaluate("() => window.__listo") is False
    pagina.clock.run_for(1_000)
    pagina.wait_for_function("() => window.__listo === true", timeout=5_000)
    assert pagina.evaluate("() => window.__resultado") == {"mensaje": _MENSAJE_SIN_CONEXION}


@pytest.mark.only_browser("chromium")
def test_crear_cobro_con_fallo_de_red_devuelve_sin_conexion(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Si la petición se corta, el mensaje pide revisar la conexión (spec 002, RF-013)."""
    abrir(pagina, servidor)
    pagina.route("**/api/cobros", _abortar)
    resultado = pagina.evaluate(
        """async () => {
          const { crear_cobro } = await import("/js/servidor.js");
          return crear_cobro(25.5, "Tacos");
        }"""
    )
    assert resultado == {"mensaje": _MENSAJE_SIN_CONEXION}


@pytest.mark.only_browser("chromium")
def test_la_direccion_del_servidor_sale_de_config_js(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """crear_cobro usa la dirección de config.js (spec 002, RF-064)."""
    servidor.fijar_config('window.PAGO_FACIL = { servidor: "/otro" };')
    abrir(pagina, servidor)
    pagina.evaluate(
        """async () => {
          const { crear_cobro } = await import("/js/servidor.js");
          return crear_cobro(25.5, "Tacos");
        }"""
    )
    assert any(
        metodo == "POST" and ruta == "/otro/api/cobros"
        for metodo, ruta, _cuerpo in servidor.peticiones
    )


@pytest.mark.only_browser("chromium")
def test_crear_y_ver_solo_piden_cosas_al_servidor_configurado(
    pagina: Page, servidor: ServidorSimulado
) -> None:
    """Crear y ver un cobro solo hablan con el origen del simulado (spec 002, RF-063)."""
    abrir(pagina, servidor)
    vistas: list[str] = []
    pagina.on("request", lambda peticion: vistas.append(peticion.url))
    pagina.evaluate(
        """async () => {
          const { crear_cobro, ver_cobro } = await import("/js/servidor.js");
          const creado = await crear_cobro(25.5, "Tacos");
          return ver_cobro(creado.cobro.id);
        }"""
    )
    assert vistas
    assert all(url.startswith(servidor.origen) for url in vistas)
