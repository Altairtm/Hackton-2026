"""Pruebas de la consulta de respaldo, repartidas del prototipo (spec 001, F1)."""


def test_sin_webhook_el_estado_se_confirma_consultando_a_pey(cliente, pey, monkeypatch) -> None:
    cobro = cliente.post("/api/cobros", json={"monto": 0.01}).json()
    assert cliente.get(f"/api/cobros/{cobro['id']}").json()["estado"] == "pendiente"

    pey.transacciones = [{"id": "01TX", "status": "PAID", "amount": 0.01, "datePaid": 1790724818}]
    # La consulta a pey se limita a una cada pocos segundos por cobro.
    monkeypatch.setattr("app.main.SEGUNDOS_ENTRE_CONSULTAS_A_PEY", 0)
    assert cliente.get(f"/api/cobros/{cobro['id']}").json()["estado"] == "pagado"


def test_cobro_inexistente_da_404(cliente) -> None:
    assert cliente.get("/api/cobros/nada").status_code == 404
    assert cliente.get("/api/cobros/nada/eventos").status_code == 404
