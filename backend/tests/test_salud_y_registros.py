"""Pruebas de la configuración y de salud (spec 001, RF-022, RF-034, RF-041)."""

from app.config import Configuracion


def test_la_configuracion_tiene_los_valores_por_defecto_del_plan() -> None:
    """Los valores nuevos salen del plan, sin leer backend/.env."""
    configuracion = Configuracion(_env_file=None)
    assert configuracion.proxies_confiables == "127.0.0.1"
    assert configuracion.gracia_segundos == 0
    assert configuracion.canales_por_ip == 10


def test_salud(cliente) -> None:
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "pey_api_key": True, "pey_webhook_secret": True}
