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

En el cierre de F2: `33 passed`, y ruff limpio.

Commit sugerido:

```text
refactor(001): modelo de cobro con pagos numerados, reloj y cliente de pey paginado (F2)
```

## F3 Historia 1: cobrar con un QR

Fecha: 2026-11-14. Un cobro de monto fijo se valida en el servidor y, si pey responde bien, devuelve el QR. El monto libre sigue fuera de este corte: `0`, `null` y un monto ausente se rechazan.

### Qué comprueban las pruebas

`test_crear_cobro_pide_el_qr_a_pey_con_vigencia_de_10_minutos_y_el_id_del_cobro` mira la petición a pey: monto `0.01`, concepto, vigencia `600`, `numRef` de hasta 7 dígitos, imagen pedida y `metadata.cobroId`. La respuesta no devuelve `metadata`.

`test_el_cobro_devuelve_todos_sus_campos` exige los 15 campos del contrato, un `id` de 12 caracteres, estado `pendiente`, vencimiento a los 600 s y ventana igual al vencimiento (gracia 0).

`test_montos_no_validos_se_rechazan_sin_llamar_a_pey` cubre negativo, tres decimales, texto, más de $100 y, en este corte, `0`, `null` y ausente. El mensaje es «Escribe un monto mayor a $0 con máximo 2 decimales» o «El monto máximo de la demo es $100», y pey no recibe la petición.

`test_el_concepto_se_limpia_y_usa_cobro_por_defecto` y `test_un_concepto_con_caracteres_no_imprimibles_se_rechaza` cubren espacios, el texto «Cobro», el máximo de 40 letras y los caracteres no imprimibles.

`test_si_pey_falla_el_cobro_no_se_guarda_y_el_mensaje_dice_la_causa` cubre llave ausente, 401, 403, mantenimiento, error 500 y sin conexión. En todos, el cobro intentado responde 404. Si crear tarda demasiado, la respuesta es 502 «No se pudo crear el cobro con pey. Intenta de nuevo.»

`test_crear_un_cobro_deja_una_linea_en_el_registro` busca una línea `INFO` con el id del cobro, el `codi_qr_id` y el `requestId`.

```bash
uv run --directory backend pytest -q tests/test_crear_cobro.py
```

### Medición del QR con imagen (CE-002)

La haces tú, con el servidor local y la llave real. Crear el cobro no mueve dinero.

1. Arranca el backend: `uv run --directory backend uvicorn app.main:app --port 8000`.
2. En otra terminal:

```bash
curl -s -w '\n%{time_total}\n' -X POST http://localhost:8000/api/cobros \
  -H 'Content-Type: application/json' \
  -d '{"monto": 0.01, "concepto": "Prueba"}'
```

3. Anota aquí el `time_total`: ____ s.

Si pasa de 3 s, se anota un TK en el §14 del plan y la decisión de la imagen pasa al issue #64.

**Medición del 2026-11-14 (Hugo):** 201, cobro real de $0.01 con imagen, `time_total` de **9.09 s**. Fue una sola medición, con el servidor recién arrancado. Pasa de 3 s, así que queda como TK-5 en el §14 del plan y la decisión pasa a #64. La respuesta de crear no trajo `requestId`, así que la línea `INFO` salió sin él, como estaba previsto.

### Cierre

```bash
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

Esperado: `53 passed`, y ruff limpio.

Commit sugerido:

```text
feat(001): crear cobro CoDi de monto fijo con pey (F3)
```
