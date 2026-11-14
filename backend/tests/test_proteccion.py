"""Pruebas del límite de cobros, repartidas del prototipo (spec 001, F1)."""


def test_limite_de_cobros_por_ip(cliente) -> None:
    estados = [cliente.post("/api/cobros", json={"monto": 1}).status_code for _ in range(6)]
    assert estados == [201] * 5 + [429]
