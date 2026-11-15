"""Pruebas de la consulta de respaldo (spec 001, RF-025, RF-027)."""

from decimal import Decimal

import httpx
import pytest

from app.pey import ClientePey, ErrorPey, PagoPey
from tests.conftest import BASE_PEY_DE_PRUEBA, PeySimulado


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


def _pagina(items: list[dict], token: str | None, request_id: str) -> dict:
    return {"items": items, "nextToken": token, "requestId": request_id}


def _pagada(identificador: str, monto: int, base: int | None, pagado_en: int) -> dict:
    transaccion: dict = {
        "id": identificador,
        "status": "PAID",
        "amount": monto,
        "datePaid": pagado_en,
    }
    if base is not None:
        transaccion["amountBreakdown"] = {"base": base, "tip": monto - base}
    return transaccion


async def _consultar(pey: PeySimulado, vistas: set[str]):
    http = httpx.AsyncClient(transport=httpx.MockTransport(pey))
    cliente = ClientePey(BASE_PEY_DE_PRUEBA, "llave-falsa", http)
    try:
        return await cliente.pagos_del_qr("ab12cd34ef", vistas)
    finally:
        await cliente.cerrar()


# El nombre lo fija la tarea y no cabe en 100 caracteres.
# fmt: off
@pytest.mark.asyncio
async def test_la_consulta_sigue_las_paginas_solo_mientras_haya_pagos_nuevos_y_solo_cuenta_los_pagados() -> None:  # noqa: E501
# fmt: on
    """Tres páginas si hay pagos nuevos; para si la tercera ya se conocía; lo normal es una."""
    pey = PeySimulado()
    pey.paginas = [
        _pagina(
            [
                {"id": "pend", "status": "PENDING", "amount": 1},
                _pagada("a", 10, 10, 100),
            ],
            "t2",
            "req-1",
        ),
        _pagina([_pagada("b", 20, None, 200)], "t3", "req-2"),
        _pagina([_pagada("c", 30, 25, 300)], None, "req-3"),
    ]
    resultado = await _consultar(pey, set())
    assert resultado.pagos == [
        PagoPey(id="a", monto=Decimal("10"), monto_base=Decimal("10"), pagado_en=100),
        PagoPey(id="b", monto=Decimal("20"), monto_base=None, pagado_en=200),
        PagoPey(id="c", monto=Decimal("30"), monto_base=Decimal("25"), pagado_en=300),
    ]
    assert resultado.paginas == 3
    assert resultado.request_id == "req-3"
    assert len([s for s in pey.solicitudes if s.method == "GET"]) == 3

    pey = PeySimulado()
    pey.paginas = [
        _pagina([_pagada("a", 10, 10, 100)], "t2", "req-1"),
        _pagina([_pagada("b", 20, None, 200)], "t3", "req-2"),
        _pagina([_pagada("c", 30, 25, 300)], "t4", "req-3"),
        _pagina([_pagada("d", 40, None, 400)], None, "req-4"),
    ]
    await _consultar(pey, {"c"})
    assert len([s for s in pey.solicitudes if s.method == "GET"]) == 3

    pey = PeySimulado()
    pey.paginas = [_pagina([_pagada("a", 10, 10, 100)], None, "req-1")]
    await _consultar(pey, set())
    assert len([s for s in pey.solicitudes if s.method == "GET"]) == 1


@pytest.mark.asyncio
async def test_si_pey_tarda_mas_de_4_segundos_la_consulta_cuenta_como_sin_respuesta() -> None:
    """Un tiempo agotado es un error de conexión y la petición espera 4 s (QP-1, RF-027)."""
    pey = PeySimulado()
    pey.tiempo_agotado = True
    with pytest.raises(ErrorPey) as error:
        await _consultar(pey, set())
    assert error.value.tipo == "sin conexión"
    assert pey.solicitudes[0].extensions["timeout"]["read"] == 4.0
