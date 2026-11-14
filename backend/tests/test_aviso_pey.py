"""Pruebas del aviso de pey, repartidas del prototipo (spec 001, F1)."""

import base64

from tests.conftest import enviar_aviso, pago


def test_webhook_marca_pagado_y_no_duplica(cliente) -> None:
    cobro = cliente.post("/api/cobros", json={"monto": 0.01, "concepto": "Tacos"}).json()

    primero = enviar_aviso(cliente, pago())
    assert primero.status_code == 200
    assert primero.json() == {"recibido": True, "procesado": True}

    # Mismo aviso reenviado, y la misma transacción con otro webhook-id.
    assert enviar_aviso(cliente, pago()).json()["procesado"] is False
    assert enviar_aviso(cliente, pago(), webhook_id="msg_2").json()["procesado"] is False

    estado = cliente.get(f"/api/cobros/{cobro['id']}").json()
    assert estado["estado"] == "pagado"
    assert estado["pagado_en"] == 1790724818


def test_webhook_sin_firma_valida_se_rechaza(cliente) -> None:
    cobro = cliente.post("/api/cobros", json={"monto": 0.01}).json()

    otro_secreto = "whsec_" + base64.b64encode(b"otro-secreto-distinto-al-bueno!!").decode()
    assert enviar_aviso(cliente, pago(), secreto=otro_secreto).status_code == 401
    assert cliente.post("/webhooks/pey", json=pago()).status_code == 401
    assert cliente.get(f"/api/cobros/{cobro['id']}").json()["estado"] == "pendiente"


def test_webhook_de_cobro_desconocido_responde_200(cliente) -> None:
    respuesta = enviar_aviso(cliente, pago() | {"codiQrId": "no-existe"})
    assert respuesta.status_code == 200
    assert respuesta.json()["procesado"] is False
