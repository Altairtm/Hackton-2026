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
