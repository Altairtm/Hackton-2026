# Guía de verificación: 001 Backend del MVP

## F1 Preparación

Fecha: 2026-11-14. El prototipo responde igual. Lo nuevo es el reloj inyectable, el pey simulado compartido, la configuración nueva y pytest-asyncio.

### Reloj falso

`RelojFalso.dormir(5)` adelanta el reloj 5 segundos y cede el control. La prueba no espera esos 5 segundos: exige que el tiempo real sea menor a 0.5 s.

```bash
uv run --directory backend pytest -q tests/test_modelo.py::test_dormir_con_el_reloj_falso_adelanta_el_tiempo_sin_esperar
```

Tiene que terminar enseguida y pasar. La otra prueba del mismo archivo comprueba que `ahora()` se queda quieto hasta `avanzar(10)`.

`crear_app` guarda el reloj en `app.state.reloj`. Las rutas siguen usando el reloj del sistema; el inyectado entra en la lógica a partir de F2.

### Pey simulado, sin salir a la red

Las pruebas arman el cliente con `httpx.MockTransport` y la base `https://pey.prueba` (`backend/tests/conftest.py`). El transporte responde dentro del proceso: crear QR, páginas con `nextToken`, errores 401, 403, 503 y 500 con `requestId`, `httpx.ConnectError` y `httpx.ReadTimeout`. El host de cada petición guardada es `pey.prueba`.

```bash
uv run --directory backend pytest -q
```

Esperado: `18 passed`.

La fixture `configuracion` usa la llave falsa `llave-falsa-NO-DEBE-SALIR` y el secreto falso `whsec_` + base64 de `secreto-falso-NO-DEBE-SALIR`. El límite de la fixture sigue en 5 cobros por minuto, que es el del prototipo, para que la prueba repartida siga esperando el 429 en el sexto cobro. El valor por defecto del servidor sigue en 10.

### pytest-asyncio

Versión fijada: **1.4.1**, publicada el **2026-10-25** (la más nueva con al menos dos semanas al 2026-10-31; ver DP-2). Está solo en el grupo `dev`.

En `backend/pyproject.toml` quedó `asyncio_default_fixture_loop_scope = "function"` (TK-4 del plan): sin esa línea, pytest-asyncio 1.4.1 avisa en cada corrida de que el alcance del bucle va a cambiar.

### Cierre

```bash
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

Los tres tienen que salir limpios. `pytest` puede mostrar el aviso ya existente de Starlette sobre `TestClient` y httpx; no viene de F1.

Commit sugerido:

```text
test(001): preparar reloj inyectable, pey simulado y pytest-asyncio (F1)
```
