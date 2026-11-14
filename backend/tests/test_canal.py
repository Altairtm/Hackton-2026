"""Pruebas del canal de avisos, repartidas del prototipo (spec 001, F1)."""

from tests.conftest import enviar_aviso, pago


def test_eventos_emite_pagado_si_el_cobro_ya_se_pago(cliente) -> None:
    cobro = cliente.post("/api/cobros", json={"monto": 0.01}).json()
    enviar_aviso(cliente, pago())

    respuesta = cliente.get(f"/api/cobros/{cobro['id']}/eventos")
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    assert "event: pagado" in respuesta.text
    assert cobro["id"] in respuesta.text
