# Guía de verificación: 001 Backend del MVP

## F1 Preparación

Fecha: 2026-11-14. El prototipo responde igual. Lo nuevo es el reloj inyectable, el pey simulado compartido, la configuración nueva y pytest-asyncio.

### Reloj falso

`RelojFalso.dormir(5)` adelanta el reloj 5 segundos y cede el control. La prueba no espera esos 5 segundos: exige que el tiempo real sea menor a 0.5 s.

```bash
uv run --directory backend pytest -q tests/test_modelo.py::test_dormir_con_el_reloj_falso_adelanta_el_tiempo_sin_esperar
```

Tiene que terminar enseguida y pasar. La otra prueba del mismo archivo comprueba que `ahora()` se queda quieto hasta `avanzar(10)`.

`crear_app` guarda el reloj en `app.state.reloj`. Desde F2, crear un cobro y calcular su estado usan ese reloj.

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

## F2 Base

Fecha: 2026-11-14. El cobro guarda una lista de pagos numerados, el estado sale del reloj y la consulta a pey recorre páginas. El aviso sigue firmándose como el prototipo y el canal sigue emitiendo `pagado`. Cada transacción nueva entra por `registrar_pago`.

### Orden de estados

En `tests/test_modelo.py`, `test_el_estado_sigue_el_orden_pagos_cancelado_vencido_pendiente` deja el orden por escrito:

1. Si hay pagos, el estado es `pagado` (también si estaba vencido o cancelado).
2. Si no hay pagos y hay `cancelado_en`, el estado es `cancelado`.
3. Si `ahora` es mayor o igual que `expira_en`, el estado es `vencido`.
4. En cualquier otro caso, el estado es `pendiente`.

`test_un_cobro_sin_pagos_vence_a_los_10_minutos` fija el corte: a los 599 s sigue pendiente y a los 600 ya venció. `test_la_ventana_de_escucha_termina_al_vencer_mas_la_gracia` comprueba gracia 0 y gracia 600: la ventana sigue abierta un segundo antes de `fin_ventana` y se cierra en ese instante.

```bash
uv run --directory backend pytest -q tests/test_modelo.py -k "estado or ventana or vence"
```

### Pagos numerados y monto distinto

`test_un_qr_reutilizado_registra_y_numera_cada_pago` registra tres transacciones en el mismo cobro. Los números quedan 1, 2 y 3, `total_recibido` es la suma, `pagado_en` es la hora del último y el estado sigue `pagado`.

`test_una_transaccion_ya_vista_no_se_registra_otra_vez` usa el mismo identificador en otro cobro y por la otra fuente: las dos veces devuelve nada.

`test_un_monto_base_distinto_se_marca_y_deja_advertencia` pide $50 y registra un base de $40. El pago queda con `monto_distinto` y el registro `pago_facil` deja un `WARNING` con el id del cobro, 50 y 40. `test_una_propina_no_cuenta_como_monto_distinto` usa base $50 y recibido $55: no hay marca ni advertencia.

```bash
uv run --directory backend pytest -q tests/test_modelo.py -k "numera or transaccion or monto"
```

### Registro INFO al arrancar

Al crear la app, `pago_facil` queda en INFO y escribe en la consola. Esta línea sale al importar el servidor:

```text
INFO pago_facil: Registros de pago_facil activos
```

```bash
uv run --directory backend python -c "import app.main"
```

### Cierre

```bash
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

Esperado: `33 passed`, y ruff limpio.

Commit sugerido:

```text
refactor(001): modelo de cobro con pagos numerados, reloj y cliente de pey paginado (F2)
```
