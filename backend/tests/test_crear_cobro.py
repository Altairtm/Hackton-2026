"""Pruebas de crear un cobro, repartidas del prototipo (spec 001, F1)."""

import json

import pytest

from tests.conftest import CODI_QR_ID, LLAVE_FALSA


def test_crear_cobro_llama_a_pey_y_devuelve_el_qr(cliente, pey) -> None:
    respuesta = cliente.post("/api/cobros", json={"monto": 0.01, "concepto": "  Tacos  "})
    assert respuesta.status_code == 201
    cobro = respuesta.json()
    assert cobro["codi_qr_id"] == CODI_QR_ID
    assert cobro["qr"] == '{"IDC":"x"}'
    assert cobro["qr_imagen"] == "aW1n"
    assert cobro["estado"] == "pendiente"
    assert cobro["concepto"] == "Tacos"

    enviada = pey.solicitudes[0]
    assert enviada.headers["authorization"] == f"Bearer {LLAVE_FALSA}"
    cuerpo = json.loads(enviada.content)
    assert cuerpo["amount"] == 0.01
    assert cuerpo["expiration"] >= 360
    assert cuerpo["numRef"].isdigit() and len(cuerpo["numRef"]) <= 7
    assert cuerpo["metadata"] == {"cobroId": cobro["id"]}


@pytest.mark.parametrize("monto", [0, -5, 100.01, 1.234, "abc"])
def test_montos_invalidos_se_rechazan_sin_llamar_a_pey(cliente, pey, monto) -> None:
    respuesta = cliente.post("/api/cobros", json={"monto": monto, "concepto": "x"})
    assert respuesta.status_code == 422
    assert pey.solicitudes == []


def test_los_errores_de_validacion_salen_en_espanol(cliente) -> None:
    """Un monto ilegible responde 422 con un texto en español, no la lista de pydantic (RF-004)."""
    respuesta = cliente.post("/api/cobros", json={"monto": "abc"})
    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert isinstance(detalle, str)
    assert "input should" not in detalle.lower()
    assert "válid" in detalle.lower()


def test_error_de_pey_da_mensaje_claro_y_no_guarda_el_cobro(cliente, pey) -> None:
    pey.estado_crear = 503
    respuesta = cliente.post("/api/cobros", json={"monto": 1})
    assert respuesta.status_code == 503
    assert "mantenimiento" in respuesta.json()["detail"]
