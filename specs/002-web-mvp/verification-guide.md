# Guía de verificación: 002 Web del MVP

## F1 Preparación

Fecha: 2026-11-15. Quedaron Playwright, el servidor simulado, las páginas de los dos celulares y el esqueleto de la web. Todavía no hay teclado, cobro ni canal en la pantalla.

### Navegadores

En `backend/pyproject.toml`, grupo `dev`:

- `pytest-playwright` **0.10.0**
- `playwright` **1.64.1**

En esta Mac (Darwin 27) los dos abrieron `about:blank`. WebKit se descargó como la compilación para macOS 26 (`webkit-mac-26`, revisión 2370) y arrancó. No hizo falta la alternativa de QP-5 y no hay TK nuevo. Los navegadores quedaron en la caché de Playwright, fuera del repositorio.

```bash
uv run --directory backend playwright install chromium webkit
```

### La página

`web/index.html` trae `lang="es"`, el viewport, la marca `PAGO FÁCIL` y la política de R-11 tal cual. `config.js` deja `servidor` en cadena vacía: el mismo origen. `estilos.css` usa `box-sizing` y no fija anchos. `js/app.js` solo lee esa dirección.

La primera corrida de las pruebas de arranque falló con 404, porque `index.html` todavía no existía. Después del esqueleto pasan.

### Comandos

```bash
uv run --directory backend pytest ../web -q
```

Esperado: `5 passed`. Son las dos pruebas de arranque, cada una en Chromium (Pixel 7) y en WebKit (iPhone 13), más una prueba sin navegador que comprueba que el servidor simulado no sirve nada de `web/tests/`. El `rootdir` es `web` (`web/pytest.ini`). No sale el `PytestDeprecationWarning` de pytest-asyncio.

### Revisión de Claude (2026-11-15)

Claude revisó lo que implementó Grok y comprobó los ayudantes de `conftest.py` con una sonda temporal, ya borrada: `reloj`, `sonidos`, `vibraciones`, `bloqueos`, `canales`, el canal del simulado (`estado`, `pago`, `cortar_canal` con 503) y que la política detecta una violación. Todo funcionaba salvo un fallo, que se corrigió:

- **El simulado servía `web/tests/`** con rutas como `/js/../tests/conftest.py`, porque comprobaba el texto de la ruta y no la ya resuelta. Ahora responde 404 (prueba `test_el_servidor_simulado_no_sirve_los_archivos_de_las_pruebas`, vista fallar antes del arreglo).
- Nombres en inglés (`_lock`, `_loop`, `sock`, `args`) pasados a español, por `AGENTS.md` §4.
- La prueba de la consola usa el tipo `ConsoleMessage` en lugar de `getattr`.
- `reloj(pagina, hora)` recibe **segundos Unix** (Playwright de Python multiplica por 1000), igual que `creado_en` y `hora_servidor`. Quedó dicho en su docstring para F2 en adelante.

pytest-playwright 0.10.0, con pytest 9.2, avisa una vez `PytestRemovedIn10Warning` por su fixture `base_url`. No viene de esta fase. El comando igual sale en 0.

```bash
uv run --directory backend ruff check --config pyproject.toml ../web
uv run --directory backend ruff format --config pyproject.toml --check ../web
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

Los cinco salen limpios. El backend da **109 passed**. T001 hablaba de 104, el conteo del día en que se escribieron las tareas; no se agregaron ni se quitaron pruebas del backend.

El aviso de Starlette sobre `TestClient` y httpx sigue ahí, igual que en la 001. No viene de F1.

### Cierre

Commit sugerido:

```text
test(002): preparar Playwright, servidor simulado y esqueleto de la web (F1)
```

## F2 Base

Fecha: 2026-11-15. Quedaron la lógica del teclado, la cuenta regresiva y los pagos avisados; crear, ver y cancelar contra el servidor; el sonido propio; el bloqueo de pantalla; y las vistas Teclado y Generando QR. Las teclas se ven y se pueden pulsar, pero todavía no cambian el monto: conectarlas es F3. Cobrar sigue desactivado con el monto vacío.

Las pruebas de esta fase se escribieron antes del código y fallaron porque faltaban los módulos (`teclado.js`, `cuenta.js`, `avisados.js`, `servidor.js`, `vistas.js`). Después de implementarlas pasan.

### Ver el teclado en local

Sigue el quickstart §3 para servir la carpeta. En F2 no hace falta el servidor real ni la llave de pey: la vista Teclado no pide un cobro.

1. Deja `web/config.js` con `servidor: ""` (el mismo origen).
2. Sirve la web:

```bash
uv run --directory backend python -m http.server 5173 --directory ../web
```

3. Abre `http://localhost:5173` en el navegador, en modo celular, a 320 px de ancho.
4. Al terminar, para ese proceso por su PID exacto (`lsof -ti tcp:5173` lo muestra y `kill <PID>` lo para). No uses `pkill`.

**Esperado**: "PAGO FÁCIL", el monto en "$", las teclas 0 a 9, el punto y Borrar, el concepto (como máximo 40 caracteres) y Cobrar desactivado. La página no se desplaza hacia los lados. Pulsar un número deja el monto en "$": el teclado de la pantalla se conecta en F3.

### Sonido sin archivo

La página no importa el sonido al abrir. En la consola de esa misma página, antes de cualquier otro `import` de `js/sonido.js`:

```javascript
const urls = [];
const Original = window.Audio;
window.Audio = function (src) {
  urls.push(String(src));
  return new Original(src);
};
window.Audio.prototype = Original.prototype;
const { desbloquear, sonar } = await import("./js/sonido.js");
desbloquear();
sonar();
console.log(urls[0]);
```

**Esperado**: la dirección empieza por `blob:`. En la pestaña Red no aparece un `.wav` ni un `.mp3`. En `web/` no hay archivo de sonido: el WAV de dos tonos se arma en memoria al importar `js/sonido.js`.

### Comandos

```bash
uv run --directory backend pytest ../web -q
uv run --directory backend ruff check --config pyproject.toml ../web
uv run --directory backend ruff format --config pyproject.toml --check ../web
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

**Esperado en la web**: `52 passed, 29 skipped`. Las 29 saltadas son las pruebas de lógica pura en WebKit: llevan `only_browser("chromium")` porque no dependen del motor. En Chromium sí corren. Entran las 5 de F1. El aviso `PytestRemovedIn10Warning` de pytest-playwright sigue igual que en F1.

**Esperado en el backend**: `109 passed`. F2 no tocó el backend. Sigue el aviso de Starlette sobre `TestClient` y httpx.

Ruff de la web y del backend queda limpio. F2 no cambió `.gitignore`: no hacía falta ningún patrón nuevo.

### Revisión de Claude de F2 (2026-11-15)

Claude revisó lo que implementó Grok: las 5 pruebas nuevas, los 7 módulos de `web/js/`, y siguió esta guía a mano en el navegador integrado (320 px). Ninguna prueba fallaba. La suite es estable (3 corridas seguidas, 52 passed y 29 skipped).

- **Corregido: la pantalla podía quedarse encendida para siempre.** Si se pedía soltar el bloqueo mientras el navegador todavía contestaba el pedido, el bloqueo llegaba después y nadie lo soltaba (RF-059). Prueba nueva `test_soltar_mientras_se_pide_el_bloqueo_no_lo_deja_pegado`, vista fallar (`soltados: 0`) antes del arreglo en `web/js/pantalla.js`.
- **Corregido, sin cambio de comportamiento:** el JSDoc de `volumen` estaba colgado de `rebobinar` en `web/js/sonido.js`, y `_abortar` en tres archivos de pruebas usaba `# type: ignore` en lugar del tipo `Route`.
- **Comprobado con el `Audio` real, sin simulacro** (las pruebas simulan `play`): el WAV que arma la página dura 0.6 s, no da error en Chromium ni en WebKit y la política de seguridad no registra ninguna violación. `fetch` sobre el `blob:` sí lo bloquea `connect-src`, como debe ser.
- **Comprobado a mano con esta guía:** la vista Teclado no desborda a 320 px, las teclas van en orden de celular, Cobrar está apagado, pulsar un número deja el monto en "$" (las teclas se conectan en F3) y el fragmento del sonido da una dirección `blob:` sin ningún `.wav` en la red. La consola no muestra errores.

Pendiente para F3, a la vista en el navegador: el campo del concepto es una caja vacía, sin texto de ayuda, y el estilo es el del navegador sin tocar. Es esperado en F2; el diseño real llega con la vista QR (T027).

### Cierre

Commit sugerido:

```text
feat(002): lógica pura, uso del servidor, sonido y vistas base de la web (F2)
```

## F3 Teclado, cobro y QR

Fecha: 2026-11-15. El teclado de la pantalla ya escribe el monto. Cobrar pide el cobro, muestra "Generando QR…" al instante y, si el servidor responde con imagen, enseña el QR con el monto, el concepto, la indicación de CoDi y una cuenta regresiva que sigue `hora_servidor`. Si el servidor rechaza, no hay conexión o el QR llega sin imagen, vuelve el teclado con el mensaje y lo escrito se conserva.

Las pruebas de pantalla se escribieron antes del código. Fallaron porque pulsar un número dejaba el monto en "$" y Cobrar seguía desactivado. La de 40 caracteres en el concepto ya pasaba: el `maxlength` venía de F2.

### Cobro de $0.01 en local, sin pagarlo

Sigue el quickstart §3. Hace falta el servidor real de la 001 en el puerto 8000. No pagues el QR: esta fase solo comprueba que se genera y que la cuenta corre.

1. En `backend/.env`, agrega `WEB_ORIGIN=http://localhost:5173` sin tocar las demás variables, y arranca el servidor como dice el quickstart de la 001.
2. En `web/config.js`, pon `servidor: "http://localhost:8000"`. Al terminar, déjalo otra vez en `""` para no guardar esa dirección.
3. Sirve la web:

```bash
uv run --directory backend python -m http.server 5173 --directory ../web
```

4. Abre `http://localhost:5173` en el navegador, en modo celular, a 320 px de ancho.
5. Teclea 0, punto, 0 y 1. El monto queda en "$0.01" y Cobrar se activa. Escribe un concepto, por ejemplo "Tacos", y pulsa Cobrar.
6. Al terminar, para el `http.server` por su PID exacto (`lsof -ti tcp:5173` y `kill <PID>`). No uses `pkill`.

**Esperado**: "Generando QR…" sale enseguida. Después se ve el QR grande, "$0.01", "Tacos", "Escanéalo desde la app de tu banco, en la opción CoDi" y una cuenta que empieza cerca de 10:00 y baja. La página no se desplaza hacia los lados. Si no hay llave de pey, el teclado vuelve con el mensaje del servidor y "$0.01" sigue escrito.

### Comandos

```bash
uv run --directory backend pytest ../web -q
uv run --directory backend ruff check --config pyproject.toml ../web
uv run --directory backend ruff format --config pyproject.toml --check ../web
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

**Esperado en la web**: `94 passed, 29 skipped`. Las 29 saltadas siguen siendo la lógica pura en WebKit. Entran las de F1 y F2. El aviso `PytestRemovedIn10Warning` de pytest-playwright sigue igual.

**Esperado en el backend**: `109 passed`. F3 no tocó el backend. Sigue el aviso de Starlette sobre `TestClient` y httpx.

Ruff de la web y del backend queda limpio.

### Revisión de Claude de F3 (2026-11-15)

Claude revisó lo que implementó Grok: las pruebas nuevas (`test_teclado.py`, `test_crear_y_mostrar_qr.py`), `app.js`, `vistas.js` y `estilos.css`. Ninguna prueba fallaba y no hizo falta corregir código. La suite es estable: 3 corridas seguidas dieron `94 passed, 29 skipped`; el backend da `109 passed` y ruff queda limpio en la web y en el backend.

- **Contra el servidor simulado, en el navegador integrado a 320 px, siguiendo los pasos de arriba:** teclear 0, punto, 0, 1 deja "$0.01" y activa Cobrar; con "Tacos" sale "Generando QR…" y después el QR (224 px de 320, el 70 %), "$0.01", "Tacos", la indicación de CoDi y una cuenta que arranca en 9:59 y baja. La página no se desplaza hacia los lados (`scrollWidth` 320) y la consola no muestra errores.
- **Los `detail` de las pruebas de rechazo (422, 429, 502 y 503) son los textos reales de `backend/app/main.py`.** El backend siempre responde `detail` como texto, así que `crear_cobro` no necesita cubrir el caso de una lista.
- **No se probó contra el servidor real:** hacerlo llama a pey. Queda para Hugo, con la llave en `backend/.env`, sin pagar el QR.
- **Paso 1 de la guía:** `WEB_ORIGIN` ya vale `http://localhost:5173` por defecto en `backend/app/config.py`. Solo hace falta agregarla si la web se sirve desde otro puerto.

**Probado por Hugo contra el servidor real (2026-11-15):** con su llave de pey, el cobro de $0.01 con "Tacos" mostró el QR. Un primer intento falló porque abrió `http://[::]:5173` (el enlace que imprime `http.server`): el backend solo permite el origen `http://localhost:5173` y rechaza el resto con `400 Disallowed CORS origin`, que la web muestra como falta de conexión. Hay que abrir `http://localhost:5173` a mano.

**Tema anotado para después:** el teclado de la computadora no escribe el monto; solo funcionan las teclas de la pantalla. La spec no pide teclado físico (ni en la spec, ni en el plan, ni en las tareas), así que agregarlo es un cambio `C-n` a la spec 002, que Hugo aprueba por separado. Para un celular no hace falta.

Pendiente para F4, a la vista en el navegador: la cuenta repinta la vista QR cada 250 ms, así que al llegar un pago (T030 en adelante) hay que parar ese intervalo antes de mostrar Pago recibido. El QR mide el 70 % del ancho (`70vw`), correcto en un celular de pie y demasiado alto en horizontal; el diseño real llega más adelante.

### Cierre

Commit sugerido:

```text
feat(002): teclado, crear el cobro y mostrar el QR con cuenta regresiva (F3)
```

## F4 Aviso de pago y respaldo del canal

Fecha: 2026-11-15. Con el QR en pantalla, un pago nuevo suena, vibra en Android y deja la vista verde "Pago recibido". Si el canal se corta, se ve "Reconectando…" sin quitar el QR, y la consulta cada 3 s descubre el pago igual. Al volver el canal se quita el aviso. El mismo pago no suena dos veces.

Las pruebas se escribieron antes del código y fallaban porque no había escucha. La de WebKit del canal rechazado además esperaba "Reconectando…" antes de adelantar el reloj: si no, la consulta todavía no estaba programada.

### Modo avión (reconexión del navegador)

Con un cobro ya en la vista QR, en el celular:

1. Activa el modo avión. **Esperado**: aparece "Reconectando…" y el QR sigue.
2. Quita el modo avión. **Esperado**: desaparece "Reconectando…".
3. Provoca un pago después. **Esperado**: suena y se ve "Pago recibido".

Esto no lo cubre la suite: el reloj de las pruebas no controla la reconexión automática del navegador (TK-1).

### Silencio del iPhone (R-7)

Pendiente, anotado como TK-2 en el plan §14. Hace falta el iPhone de Hugo. No queda dicho si suena o no.

1. Sirve la web en la red local, como el quickstart §3, pero con la IP de la Mac en lugar de `localhost` (en `config.js` y en `WEB_ORIGIN`).
2. Abre esa dirección en el iPhone, crea un cobro y pon el teléfono en silencio.
3. Provoca un pago (simulado, o $0.01 real si Hugo lo autoriza en ese momento).
4. Anota en TK-2 si se oyó el sonido.

Al terminar, deja `web/config.js` con `servidor: ""`.

### Comprobado en el navegador, contra el simulado

A 320 px: teclear 25.50 y "Tacos", pulsar Cobrar, y al llegar el pago se ve la pantalla verde con "Pago recibido", "$25.50" y "Tacos". El QR se oculta. `scrollWidth` queda en 320 y la marca sigue visible. El modo avión y el silencio del iPhone no se probaron aquí.

### Comandos

```bash
uv run --directory backend pytest ../web -q
uv run --directory backend ruff check --config pyproject.toml ../web
uv run --directory backend ruff format --config pyproject.toml --check ../web
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

**Esperado en la web**: `122 passed, 29 skipped`. Las 29 saltadas siguen siendo la lógica pura en WebKit. El aviso `PytestRemovedIn10Warning` de pytest-playwright sigue igual.

**Esperado en el backend**: `109 passed`. F4 no tocó el backend. Sigue el aviso de Starlette sobre `TestClient` y httpx.

Ruff de la web y del backend queda limpio.

### Revisión de Claude de F4 (2026-11-15)

Claude revisó lo que implementó Grok: `web/js/escucha.js`, `vistas.js`, `app.js`, `estilos.css` y las pruebas de `test_pago_recibido.py` y `test_respaldo.py`. Ninguna prueba fallaba. La suite es estable: 5 corridas seguidas dieron `122 passed, 29 skipped`; el backend da `109 passed` y ruff queda limpio en la web y en el backend.

- **Corregido: monto distinto sin rótulos.** La vista mostraba `$25.50 $20.00`, sin decir cuál se pidió y cuál llegó (RF-028). Ahora dice `Pediste $25.50, recibiste $20.00`. La prueba `test_un_monto_distinto_muestra_el_pedido_y_el_recibido` ganó esa comprobación y se vio fallar (`Actual value: $25.50 $20.00`) antes del arreglo en `web/js/vistas.js`.
- **Corregido, sin cambio de comportamiento:** `_abortar_consulta` en `test_respaldo.py` no tenía tipo de retorno (`AGENTS.md` §5).
- **Los eventos del simulado coinciden con los del backend real** (`backend/app/canal.py` y `respaldo.py`): `estado` trae el cobro y `pago` trae `{pago, cobro}`, que es lo que lee `escucha.js`.
- **Comprobado a mano, contra el simulado, a 320 px, siguiendo esta guía:** con el QR en pantalla se cortó el canal y salió «Reconectando…» sin quitar el QR. Un pago sin aviso por el canal lo descubrió la consulta de 3 s y la pantalla se puso verde con "Pago recibido", "$25.50" y "Tacos"; el QR se oculta y la cuenta se detiene. Al restaurar el canal desapareció «Reconectando…», y un segundo pago de $20.00 con monto distinto mostró el rótulo nuevo. `scrollWidth` quedó en 320. La consola solo mostró el `503` que provoqué al cortar el canal y el aviso de Chrome de que bloquea `vibrate` si no hubo un toque real: las pruebas hicieron los toques por código, en un celular real sí vibra.

Pendiente, a la vista en el navegador:

- El texto blanco de "Pago recibido" sobre el verde `#128a3e` tiene un contraste de unos 4.4:1, justo debajo del 4.5:1 recomendado para texto pequeño. El monto grande sí pasa. El diseño real llega más adelante.
- `estilos.css` pinta el fondo con `body:has(...)`, que necesita iOS 15.4 o más. Si el iPhone de la prueba del silencio es más viejo, la pantalla no se verá verde.
- El silencio del iPhone y el modo avión siguen sin probarse (TK-2 y TK-1): necesitan el celular de Hugo.

### Cierre

Commit sugerido:

```text
feat(002): aviso de pago con sonido, vibración y respaldo del canal (F4)
```

## F5 QR vencido, Nuevo cobro y vista Error

Fecha: 2026-11-15. Si el QR cumple 10 minutos sin un pago, se oculta y queda "QR vencido", con el aviso de que un pago tardío todavía se avisa. Con un pago ya recibido, al llegar a 0:00 la pantalla se queda en verde. `fin`, o una consulta con la hora del servidor ya pasada de `fin_ventana`, cierra el canal y no vuelve a preguntar. Si el servidor ya no conoce el cobro, se ve la vista Error. Nuevo cobro, desde QR, QR vencido, Pago recibido o Error, vuelve al teclado vacío y deja de escuchar ese cobro. Las teclas y los botones miden al menos 44 px de alto.

### Verlo en local, sin pagar

Sirve la web como en F2 (`servidor: ""`) o contra el simulado. Con el servidor real, un cobro de $0.01 sigue el quickstart §5; no lo pagues si solo quieres ver el vencimiento.

1. Teclea un monto, escribe un concepto y pulsa Cobrar.
2. Pulsa Nuevo cobro. **Esperado**: el teclado vuelve vacío. Un pago de ese QR ya no cambia la pantalla.
3. Crea otro cobro y espera 10 minutos sin pagarlo. **Esperado**: desaparece el QR y se lee "QR vencido", el monto, el concepto y "Si el cliente ya pagó, aquí te avisamos".
4. Si ese cobro se pagara dentro de los siguientes 10 minutos, sonaría y se vería "Pago recibido".

Los pagos reales del corte 1 (quickstart §5 y §6) quedan pendientes: hace falta tu autorización y la web en HTTPS. No se hicieron en esta sesión.

### Revisión de seguridad del corte 1

- Secretos: `git grep -nE "whsec_|Bearer |PEY_API_KEY|PEY_WEBHOOK_SECRET|pey\\.mx" -- web` no encontró nada.
- Textos de fuera: `git grep -n "innerHTML\\|outerHTML\\|insertAdjacentHTML\\|document.write" -- web/js` no encontró nada. El concepto, los mensajes y los montos se pintan con `textContent`.
- La política de `web/index.html` es la de R-11: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self' http://localhost:8000 https:`.
- Un pago solo se anuncia en `escucha.js` cuando el servidor trae un pago nuevo en el cobro (`sonar` y `vibrar` dentro de ese recorrido). La pantalla no marca un pago por su cuenta.
- Cobrar y Monto libre se ignoran mientras `accion_en_curso` está ocupada. La web no reintenta crear un cobro sola.

### Comandos

```bash
uv run --directory backend pytest ../web -q
uv run --directory backend ruff check --config pyproject.toml ../web
uv run --directory backend ruff format --config pyproject.toml --check ../web
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

**Esperado en la web**: `176 passed, 29 skipped`. Las 29 saltadas siguen siendo la lógica pura en WebKit.

**Esperado en el backend**: `109 passed`. F5 no tocó el backend.

### Revisión de Claude de F5 (2026-11-15)

Claude revisó `escucha.js`, `vistas.js`, `app.js`, `estilos.css`, `test_vencido_y_nuevo.py` y `test_seguridad.py`. Ninguna prueba fallaba y el comportamiento es el de la spec. La suite es estable: 7 corridas seguidas dieron `176 passed, 29 skipped`.

- **Corregido: la suite tardaba 4.5 minutos** (F4 tardaba 1). Seis pruebas saltaban 5 o 10 minutos con `clock.run_for`, que dispara el intervalo de la cuenta unas 2400 veces: 11 s en Chromium y 19 s en WebKit cada una. Pasaron a `clock.fast_forward`, que dispara los temporizadores una vez; la cuenta se recalcula con `Date.now()`, igual que cuando el celular se duerme. Las mismas 176 pruebas pasan en unos 100 s. Anotado como TK-3 en el plan.
- **Corregido, sin cambio de comportamiento:** `_visible` en `test_vencido_y_nuevo.py` no tenía tipo de retorno, y el JSDoc de `empezar_cuenta` estaba colgado encima de `tiene_pagos`, en `app.js`.
- **Revisión de seguridad (T042), repetida por Claude:** los dos `git grep` salen vacíos (secretos y HTML inyectado), la política de `web/index.html` es la de R-11 con los ajustes de QP-2, `crear_cobro` solo se llama desde `pedir_cobro` y un pago solo se anuncia desde `escucha.js` con un cobro del servidor.
- **Comprobado a mano, contra el simulado, a 320 px:** con el QR en pantalla, el evento `vencido` oculta el QR y deja "QR vencido", "$25.50", "Tacos" y "Si el cliente ya pagó, aquí te avisamos". Un pago tardío con el QR vencido muestra "Pago recibido". Con el cobro olvidado y el canal rechazado con 404, la consulta lleva a la vista Error con el texto de RF-057. Nuevo cobro, desde QR, Pago recibido y Error, deja el teclado en "$" y sin concepto. La página no se desplaza hacia los lados y los botones visibles miden 44 px.
- **No se probó:** los pagos reales (quickstart §5 y §6), el silencio del iPhone y el modo avión. Esperan a CoDi y a tu celular.

### Cierre

Commit sugerido:

```text
feat(002): QR vencido, Nuevo cobro y vista de error (F5)
```

## F6 Monto libre, número de pago y Mostrar QR otra vez

Fecha: 2026-11-15. Con el monto vacío o en cero, Monto libre pide un cobro sin monto y el QR dice "Monto libre". Con un monto mayor a cero, la tecla está apagada. Desde el segundo pago se ven "Pago 2" y el total. Mientras el QR siga vigente, "Mostrar QR otra vez" vuelve a enseñarlo; si ese QR llega a 0:00, regresa a Pago recibido y no a QR vencido. Un pago nuevo con el QR reabierto suena y vuelve a la pantalla verde.

### Verlo en local

1. Deja el concepto, por ejemplo "Propina", y pulsa Monto libre sin teclear un monto. **Esperado**: "Generando QR…" y después el QR con "Monto libre" y "Propina". Cobrar sigue apagado.
2. Teclea 25.50. **Esperado**: Monto libre se apaga y Cobrar se prende.
3. Cobra $25.50. Cuando llegue un pago, se ve "Pago recibido" sin "Pago 1". Un segundo pago al mismo QR muestra "Pago 2" y el total.
4. Antes de que pasen 10 minutos, pulsa "Mostrar QR otra vez". **Esperado**: vuelve el QR y su cuenta. Si se acaba el tiempo, vuelve "Pago recibido".

El pago real de monto libre y el segundo pago de $0.01 (quickstart §7) quedan pendientes: hace falta tu autorización. No se hicieron en esta sesión.

### Revisión de Claude de F6 (2026-11-15)

Claude revisó `test_monto_libre_y_reuso.py`, y `vistas.js` y `app.js` en lo de Monto libre, "Pago n" y Mostrar QR otra vez. Ninguna prueba fallaba. Los campos que usa (`monto: null`, `fin_ventana`, `total_recibido`, `pagos[].numero`) existen en `backend/app/cobros.py`, y el backend acepta `monto: null` como monto libre (`validar_monto`).

- **Corregido: el total sin rótulo.** Desde el segundo pago la vista mostraba "Pago 2" y "$35.50" sin decir que era la suma, bajo un monto grande que es el del último pago. Ahora dice `Total recibido: $35.50` (igual que el rótulo de monto distinto de F4). La prueba `test_el_segundo_pago_muestra_pago_2_y_el_total` ganó esa comprobación y se vio fallar (`Actual value: $35.50`) antes del arreglo en `web/js/vistas.js`.
- **Corregido, sin cambio de comportamiento:** una asignación sin uso de `id_cobro` en `test_mostrar_qr_otra_vez_vuelve_al_qr_mientras_siga_vigente`.
- **Comprobado a mano, contra el simulado, a 320 px:** sin teclear monto, Monto libre crea el QR con "Monto libre" y "Propina"; con 25 tecleado se apaga y Cobrar se prende. Dos pagos (12 y 5) dejaron "Pago 2" y "Total recibido: $17.00", sin "monto distinto". "Mostrar QR otra vez" volvió al QR con su cuenta (9:35) y "Monto libre".
- **No se probó:** los pagos reales de $0.01 (quickstart §7).

### Cierre

Commit sugerido, si F5 y F6 van juntas:

```text
feat(002): QR vencido, monto libre, número de pago y mostrar el QR otra vez (F5 y F6)
```

Si se separan, el de F6 es:

```text
feat(002): monto libre, número de pago y mostrar el QR otra vez (F6)
```

## F7 Cobros anteriores y Cancelar cobro

Fecha: 2026-11-15. Nuevo cobro deja el cobro como anterior y lo sigue escuchando hasta el fin de su ventana. Un pago a ese cobro suena, vibra en Chromium y muestra un aviso con el monto y el concepto, sin borrar lo que se está tecleando; el aviso se cierra al tocarlo. Hay como máximo 3 canales: el cobro en pantalla y los dos anteriores más recientes. El resto se consulta cada 3 segundos, y al cerrarse un canal el siguiente más reciente abre el suyo. La pantalla sigue encendida mientras quede cualquier escucha.

Cancelar cobro aparece en el QR de un cobro pendiente. Mientras el servidor responde, el botón dice "Cancelando…" y un segundo toque no repite el pedido. Si el servidor confirma, vuelve el teclado vacío y el cobro se sigue escuchando: un pago posterior suena y muestra el aviso. Si rechaza (404, 409 o sin conexión), el QR se queda con el mensaje. Un `cancelado` que llega por el canal, sin que esta pantalla lo haya pedido, hace lo mismo que una cancelación confirmada.

Se quitó `test_en_el_corte_1_nuevo_cobro_deja_de_escuchar_el_cobro`: en el corte 2 Nuevo cobro ya no corta la escucha. La prueba de soltar la pantalla, tras Nuevo cobro, espera el `fin` del cobro anterior.

### Verlo en local

Hace falta el servidor simulado o el servidor real. Con el simulado, las pruebas de `web/tests/test_cobros_anteriores.py` recorren los dos flujos. A mano, con la web y el servidor en marcha:

1. Crea un cobro, por ejemplo $30 "Refresco", pulsa Nuevo cobro y teclea otro monto. Paga el QR anterior. **Esperado**: suena, aparece el aviso de $30.00 y "Refresco", y el monto tecleado sigue ahí. Al tocar el aviso, se cierra.
2. Crea otro cobro y pulsa Cancelar cobro. **Esperado**: un momento "Cancelando…" y después el teclado vacío. El QR sigue pagable: al pagarlo, suena y aparece el aviso.

Los pagos reales de $0.01 (quickstart §7, "Cobro anterior" y "Cancelar") quedan pendientes: hace falta tu autorización. No se hicieron en esta sesión.

### Comandos

```bash
uv run --directory backend pytest ../web -q
uv run --directory backend ruff check --config pyproject.toml ../web
uv run --directory backend ruff format --config pyproject.toml --check ../web
uv run --directory backend pytest -q
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
```

La web: **206 passed, 29 skipped**. El backend: **109 passed**. Ruff, en los dos, limpio. Los 29 saltos son las pruebas marcadas `only_browser("chromium")` cuando les toca WebKit. El aviso de pytest-playwright sobre `base_url` sigue igual que en F1, y el de Starlette sobre `TestClient` igual que en la 001.

### Revisión de Claude de F7 (2026-11-15)

Claude revisó el diff de `escucha.js` (`tomar_canal`, `soltar_canal`, `_repartir`, `cancelado`), `app.js` (`al_cancelar`, `volver_al_teclado`, `pintar_qr_actual`), `vistas.js`, el simulado y las pruebas de `test_cobros_anteriores.py`. El reparto de 3 canales coincide con QP-1 y con data-model §2, y las 14 pruebas nuevas cubren los escenarios de T049 y T050. Ninguna fallaba.

- **Corregido: el aviso del cobro anterior quedaba fuera de la pantalla.** Se anexaba al final de la página sin estilo. A 320×568, en la vista verde «Pago recibido», su borde superior caía en 584 px, con la pantalla en 568: el dueño no lo veía sin desplazarse. Ahora es una franja fija arriba, encima de cualquier vista (`web/estilos.css`). La prueba `test_el_aviso_de_un_cobro_anterior_se_ve_sin_desplazar_la_pantalla_y_dice_que_es` se vio fallar antes del arreglo.
- **Corregido: el aviso sin rótulo.** Decía solo «$30.00 Refresco». Ahora dice `Pago de un cobro anterior: $30.00 Refresco` (mismo tipo de fallo que el rótulo de monto distinto de F4 y el del total de F6). Cambio en `web/js/vistas.js`.
- **Comprobado a mano, contra el simulado, a 320 px:** con el teclado, un pago al cobro anterior deja el aviso arriba sin borrar el "$12" tecleado; en la vista QR y en «Pago recibido» el aviso queda a la vista; un concepto de 40 caracteres se envuelve en dos líneas.
- **Pendiente para F8:** si dos cobros anteriores se pagan seguidos, el segundo aviso reemplaza al primero (un solo elemento `aviso-anterior`). Los dos suenan, pero solo queda visible el último. RF-075 pide un aviso por cada pago recuperado, así que F8 tendrá que acumularlos; conviene decidirlo entonces.
- **Resultados:** web **208 passed, 29 skipped** (107 s); backend **109 passed**; `ruff check` y `ruff format --check` limpios en web y backend.
- **No se probó:** los pagos reales de $0.01 (quickstart §7, «Cobro anterior» y «Cancelar»).

### Cierre

Commit sugerido:

```text
feat(002): escuchar cobros anteriores y cancelar un cobro (F7)
```
