"""Pruebas del reloj inyectable (spec 001, principio V)."""

import time

import pytest

from app.reloj import RelojFalso


def test_el_reloj_falso_avanza_solo_cuando_se_le_pide() -> None:
    """El reloj falso no se mueve hasta que la prueba llama a avanzar."""
    reloj = RelojFalso(inicio=1_794_700_000)
    assert reloj.ahora() == 1_794_700_000
    reloj.avanzar(10)
    assert reloj.ahora() == 1_794_700_010


@pytest.mark.asyncio
async def test_dormir_con_el_reloj_falso_adelanta_el_tiempo_sin_esperar() -> None:
    """dormir adelanta el reloj y no espera los segundos pedidos."""
    reloj = RelojFalso(inicio=1_794_700_000)
    inicio_real = time.perf_counter()
    await reloj.dormir(5)
    assert reloj.ahora() == 1_794_700_005
    assert time.perf_counter() - inicio_real < 0.5
