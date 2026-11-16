# Nota de implementación: #64 MVP web: una página de cobro con monto, QR y sonido de pago recibido

- **Issue**: #64
- **Quién lo hizo**: Hugo Portillo, con agentes de IA: Grok implementó las fases y Claude y Codex las revisaron y corrigieron
- **Fecha**: 2026-11-16
- **Rama y pull request**: `feature/64-web-mvp` · #72

## 1. Qué pedía el issue

Una página, pensada primero para celular, donde el negocio teclea el monto, ve el QR CoDi en grande y oye un sonido cuando le pagan. Es la versión mínima de #31 (pantalla de cobro) y #32 (sonido y aviso), sobre el backend de #62 y #63.

## 2. Qué se hizo

La carpeta `web/` tiene una sola página (HTML, CSS y JavaScript con módulos, sin framework ni paso de compilación). Hace lo que el issue pide y los dos cortes de la spec:

- **Corte 1:** teclado con monto fijo, QR con cuenta regresiva, sonido, vibración y «Pago recibido» en verde, respaldo si se corta el canal, QR vencido, Nuevo cobro y pantalla encendida mientras haya un cobro en escucha.
- **Corte 2:** Monto libre, «Pago n» con el total, Mostrar QR otra vez, cobros anteriores que siguen avisando, Cancelar cobro y recuperar los cobros al recargar la página.

Archivos principales: `web/index.html`, `web/estilos.css`, `web/config.js` (la única dirección del servidor) y `web/js/` (`app.js`, `vistas.js`, `escucha.js`, `servidor.js`, `memoria.js`, `sonido.js`, `pantalla.js`, y la lógica pura de `teclado.js`, `cuenta.js` y `avisados.js`). Las pruebas están en `web/tests/`.

La spec, el plan, las tareas y la guía de verificación están en [`specs/002-web-mvp/`](../../specs/002-web-mvp/). No se repiten aquí.

## 3. Decisiones y por qué

Todas están en el [plan](../../specs/002-web-mvp/plan.md) (DP-n y registro de implementación TK-n). Las que más pesan:

- **Sin framework.** Una pantalla no justificaba uno, y así no hay librerías que auditar ni compilar. JavaScript con módulos y `textContent` en lugar de `innerHTML`.
- **Sonido propio.** El sonido es un WAV que la página arma en memoria al cargar, no un archivo: no hay audio de terceros ni licencia que anotar. Se «desbloquea» al pulsar Cobrar porque los navegadores bloquean el audio hasta el primer toque.
- **Canal de eventos con respaldo.** La página escucha el canal del cobro (SSE) y, si se corta, consulta el estado cada 3 s y reintenta el canal cada 15 s. El navegador solo abre 6 conexiones por origen, así que hay como máximo 3 canales por pantalla (el cobro en pantalla y los dos anteriores más recientes); el resto se consulta.
- **Hora del servidor.** La cuenta regresiva usa el desfase con la hora del servidor (`hora_servidor`, cambio C-2 a la spec 001), no el reloj del celular.
- **Seguridad.** Todo texto de fuera (concepto, mensajes, lo recordado en el celular) se pinta solo como texto. `localStorage` guarda únicamente identificadores de cobro y se valida al leerlos. La política de seguridad de contenido está en `web/index.html`. La web no tiene llaves ni habla con pey.
- **Las pruebas no esperan el reloj real.** `ServidorSimulado` hace de servidor y `page.clock` controla el tiempo (TK-1 y TK-3 del plan).

## 4. Cómo probarlo

Automático (desde la raíz; la primera vez, instala los navegadores de las pruebas):

```bash
uv run --directory backend playwright install chromium webkit
uv run --directory backend pytest ../web -q
uv run --directory backend pytest -q
```

Esperado: web `243 passed, 32 skipped` (Chromium y WebKit; la lógica pura solo corre en Chromium) y backend `109 passed`. Ruff queda limpio en los dos.

A mano, con el backend en el puerto 8000: `web/config.js` con `servidor: "http://localhost:8000"` y la web servida con `uv run --directory backend python -m http.server 5173 --directory ../web`. Se abre **`http://localhost:5173`**, no el enlace `[::]`. Los pasos y lo esperado están en el [quickstart](../../specs/002-web-mvp/quickstart.md) y en la [guía de verificación](../../specs/002-web-mvp/verification-guide.md).

Pruebas reales con CoDi, de $0.01 el 2026-11-16, en computadora: cobro, cobro anterior, cancelar, recargar y monto libre funcionaron.

## 5. Qué quedó pendiente

- **El criterio de #64 no está completo.** Falta comprobar en Android (Chrome) y en iPhone (Safari), con la web en HTTPS: sonido y vibración, el iPhone en silencio (TK-2), el modo avión (TK-1) y la pantalla encendida 10 minutos. Tampoco se pudo medir «suena en menos de 2 s»: sin webhook, pey tardó más de 30 s en reportar el primer pago. Por eso el PR usa `Refs #64` y no `Closes #64`.
- **Despliegue (#65):** poner la dirección real del servidor en `config.js` y en `WEB_ORIGIN`, y cambiar `https:` y `http://localhost:8000` de `connect-src` en `web/index.html` por el dominio exacto.
- **Contraste de «Pago recibido»:** 4.4:1, queda para #42.
- **Teclado físico de la computadora:** no está en la spec; hace falta un cambio `C-n` si se quiere.
- **Avisos de cobros anteriores:** se apilan sin tope de alto. Con unos 8 o más seguidos taparían Nuevo cobro hasta tocarlos.
- **iOS anteriores a 15.4:** el fondo verde usa `body:has()`.
- **Reparto de #64:** está asignado a Miguel y lo implementó Hugo; este PR cubre buena parte de #31, #32 y #41. Hay que acordar con Miguel qué le queda.

## 6. Seguridad

- [x] Ninguna llave, secreto ni dato personal real quedó en el código, en la nota ni en las capturas.
- [x] Ninguna pantalla habla con pey directamente.
