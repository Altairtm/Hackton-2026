# Investigación (Fase 0): Spec 001 — Backend del MVP

- **Fecha**: 2026-11-14
- **Plan**: [plan.md](plan.md)
- **Fuentes**: código del prototipo en `backend/`, `openapi.json` y páginas de webhooks de pey (descargados el 14 nov), versiones instaladas en `backend/uv.lock`.

Cada sección sigue el formato de spec-kit: **Decisión**, **Por qué** y **Alternativas consideradas**. Las que decidió Hugo están marcadas con *(decidió Hugo)* y se resumen como DP en el plan (§9.2).

---

## R-1. Partir del prototipo o reescribir *(decidió Hugo, DP-1)*

- **Decisión** (Hugo, 2026-11-14): partir del prototipo y reorganizarlo, con pruebas primero.
  - Se conservan el cliente de pey, la verificación de firma y la configuración.
  - Se rehacen el modelo de cobro (varios pagos y reloj inyectable) y el canal de avisos (ventana de escucha y consulta automática a pey).
- **Por qué**:
  - El cliente de pey ya funcionó contra el pey real el 14 nov.
  - 11 de las 15 pruebas siguen valiendo con cambios menores.
  - QA-10 dice que manda la spec, no que haya que tirar el código.
- **Alternativas consideradas**:
  - **Reescribir desde cero, con pruebas primero**: más limpio para el principio V, pero tarda más y pone en riesgo la entrega del domingo.
  - **Usar el prototipo tal cual en el corte M0**: no cumple RF-040 (consulta automática), RF-041 ni QA-6, que son del corte M0.

## R-2. Tiempo controlado en las pruebas *(principio V)*

- **Decisión**: un `Reloj` propio que se inyecta.
  - Tiene `ahora()` (segundos Unix) y `dormir(segundos)`.
  - En producción usa `time.time()` y `asyncio.sleep`.
  - En las pruebas, `RelojFalso` avanza el tiempo a mano: su `dormir` adelanta el reloj y cede el control sin esperar de verdad.
- **Por qué**: la constitución prohíbe que las pruebas dependan del reloj real. Vencimiento, ventana de escucha, límites por minuto y consulta cada 5 s dependen del tiempo. Con un reloj inyectado, una prueba de "10 minutos" corre en milisegundos.
- **Alternativas consideradas**:
  - **`freezegun` o `time-machine`**: son librerías nuevas, que exigen comparativa, y no controlan bien `asyncio.sleep`.
  - **`monkeypatch` de `time.time`**: frágil, y no cubre las esperas.

## R-3. Pruebas asíncronas del canal *(decidió Hugo, DP-2)*

- **Decisión**: **pytest-asyncio** (`@pytest.mark.asyncio`), elegido por Hugo el 2026-11-14 frente a la recomendación (el plugin de anyio).
  - Se agrega en F1 al grupo `dev` con `uv add --dev pytest-asyncio`, fijado a una versión publicada hace al menos dos semanas.
  - Es solo de desarrollo: no llega al servidor desplegado.
- **Por qué**: el canal de avisos es un generador asíncrono que vive minutos. `TestClient` no puede probarlo sin esperar, porque lee la respuesta completa. Se prueba el generador directamente, con `RelojFalso`.
- **Comparativa**:

| | A. Plugin de anyio (recomendada por Claude) | B. `pytest-asyncio` (elegida por Hugo) |
|---|---|---|
| Instalación | Ya instalado; solo se declara | Paquete nuevo |
| Uso | `@pytest.mark.anyio` y un fixture `anyio_backend` | `@pytest.mark.asyncio` |
| Ventajas | Cero dependencias nuevas; es lo que usan `httpx` y `starlette` | Muy conocido y con mucha documentación |
| Desventajas | Menos tutoriales | Una dependencia más, con cambios de configuración entre versiones |
| Curva de aprendizaje | Baja: un decorador | Baja: un decorador |

## R-4. Canal de avisos con Server-Sent Events

- **Decisión**:
  - Un generador asíncrono por conexión, con un solo ciclo que espera el próximo evento con un tiempo límite.
  - El tiempo límite es el menor de: 5 s (consulta a pey), lo que falta para el vencimiento y lo que falta para el fin de la ventana.
  - En cada vuelta: emite los eventos encolados, detecta el paso a *vencido*, consulta a pey si toca y manda una señal de vida si pasaron 15 s sin enviar nada.
- **Por qué**:
  - Con vueltas de 5 s como máximo, *vencido* se emite en menos de 15 s (RF-030, QA-5) y la consulta automática cumple RF-040 sin tareas de fondo.
  - Si no hay pantalla conectada, no hay consultas, lo que acota el uso del API de pey (RF-041).
- **Evento `fin`**: `EventSource` se reconecta solo cuando el servidor cierra la conexión. Si el servidor cierra al terminar la ventana (RF-032), el navegador volvería a abrir el canal cada 3 s, recibiría el estado y otra vez el cierre (RF-043), en un ciclo sin fin.
  - Por eso, antes de cerrar, el servidor emite el evento `fin` y el contrato obliga a la web a llamar a `close()` al recibirlo.
  - Un 404 o un 429 también detienen la reconexión del navegador.
- **Alternativas consideradas**:
  - **Una tarea de fondo por cobro que consulta a pey**: consulta aunque nadie mire y complica el cierre limpio.
  - **WebSockets**: más complejos; no hace falta enviar nada del navegador al servidor.

## R-5. IP real del cliente detrás del proxy del hosting (QA-6)

- **Decisión**: agregar dentro de la app el `ProxyHeadersMiddleware` que ya trae uvicorn (0.54.0).
  - Usa la cabecera `X-Forwarded-For` solo cuando la petición viene de un proxy de confianza, configurado con la variable `PROXIES_CONFIABLES`.
  - En local vale `127.0.0.1`. En el hosting vale la IP del proxy, o `*` si el hosting no permite conexiones directas al servidor (lo confirma Altairtm en #65).
- **Por qué**: no agrega librerías y, al vivir dentro de la app, se prueba con `TestClient` mandando cabeceras. `request.client.host` pasa a ser la IP real y el límite por IP no cambia de código.
- **Alternativas consideradas**:
  - **La opción `--proxy-headers` de uvicorn al arrancar**: hace lo mismo, pero no se puede probar automáticamente y depende del comando de arranque.
  - **Leer `X-Forwarded-For` a mano**: es fácil equivocarse y dejar que un visitante falsifique su IP.

## R-6. Pagos de pey: paginación, estados y desglose (QA-4, errata 2)

- **Hechos del API**:
  - `GET /transaction/codi/qr/{id}` devuelve hasta 20 transacciones por página, de la más nueva a la más vieja, con `nextToken`.
  - Cada transacción tiene `status`, que puede ser `PENDING` o `PAID`, `amount` (total) y `amountBreakdown` con `base`, `tip` y `fee`.
  - El aviso de pey solo trae `amount` ("the amount received") y `transactionId` (un ULID, igual que el `id` de la consulta).
- **Decisión** (ajustada por QP-2):
  - El cliente de pey sigue `nextToken` solo mientras la página traiga transacciones que no están en el conjunto de vistas. Como pey ordena de la más nueva a la más vieja, lo normal es una sola petición. Devuelve solo las `PAID` como `PagoPey(id, monto, monto_base, pagado_en)`.
  - `monto_base` es `amountBreakdown.base` cuando existe, y vacío cuando no.
  - Un pago que llega por el aviso no trae `monto_base`, así que el monto distinto se compara con el total (RF-019).
- **Por qué**: un QR no tiene límite de pagos (E-4), y una transacción `PENDING` no es un pago (errata 1).
- **Alternativas consideradas**:
  - **Leer solo la primera página**: pierde pagos después del número 20.
  - **Recorrer todas las páginas con tope de 50**: era la propuesta inicial; QP-2 la descartó por el número de peticiones.

## R-7. Mensajes de error en español para el dueño

- **Decisión**: todas las respuestas de error usan el mismo cuerpo, `{"detail": "<mensaje en español para el dueño>"}`.
  - Un manejador de `RequestValidationError` convierte los errores de validación, que FastAPI da en inglés y como lista, en un solo mensaje en español.
- **Por qué**: el principio VII pide mensajes para el dueño. Hoy un concepto o un monto inválido devuelve el detalle técnico de pydantic.
- **Alternativas consideradas**: dejar el formato de FastAPI y traducir en la web, lo que reparte la responsabilidad del mensaje entre dos specs.

## R-8. Deduplicación del aviso de pey (QA-10)

- **Decisión**:
  - El `webhook-id` se marca como visto solo **después** de procesar el aviso, o cuando se ignora a propósito (otro tipo de evento o cobro desconocido).
  - Si el procesamiento falla (por ejemplo, un monto que no se puede leer), no se marca, para que el reintento de pey se procese.
  - La barrera definitiva sigue siendo el `transactionId` (principio II).
- **Por qué**: hoy el prototipo lo marca antes (`main.py:210`), y un fallo transitorio haría que se ignorara el reintento.

## R-9. Registros visibles (RF-039, QA-10)

- **Decisión**: la app configura el registro `pago_facil` en nivel INFO, con su propio formato, al crearse, salvo que las pruebas lo desactiven.
  - Cada mensaje incluye el id del cobro y, en los errores de pey, el `requestId`.
  - Cada interacción con pey deja una línea `INFO`: cada QR creado (id y `codi_qr_id`) y cada consulta (id del cobro, páginas pedidas y pagos nuevos), con `requestId` cuando pey lo mande (principio X, QT-4).
  - Nunca incluye la llave, el secreto, cabeceras de autorización ni el cuerpo completo del aviso.
- **Por qué**: hoy los mensajes INFO no se ven al correr uvicorn (`logging` sin configurar).

## R-10. Montos en el JSON

- **Decisión**: los montos se manejan como `Decimal` y salen en el JSON como número con 2 decimales.
  - El monto libre sale como `"monto": null` con `"monto_libre": true`.
  - Los nombres de los campos van en español y en `snake_case`, incluido `codi_qr_id`. El prototipo mezclaba `codiQrId`, `qrImagen` y `creado_en`; como la web todavía no existe, se unifica ahora.
- **Por qué**: así no hay errores de redondeo en las comparaciones, y es un solo estilo de nombres (constitución, idioma).
- **Alternativas consideradas**: montos como texto ("12.50"), que es más exacto pero incómodo para la web.

## R-11. Tiempos de espera con pey (QP-1)

- **Decisión**: 4 s por petición en la consulta de respaldo y 10 s para crear el QR. Un tiempo agotado se trata como "sin conexión": en la consulta se devuelve el último estado (RF-027); al crear, 502 con "Intenta de nuevo".
- **Por qué**: con los 20 s del prototipo, una consulta lenta dentro del ciclo del canal impediría emitir *vencido* en menos de 15 s (RF-030) y la señal de vida cada 15 s (RF-033). Crear el QR tiene la meta de 3 s (CE-002), y 10 s es el máximo razonable antes de pedir que se reintente.
- **Alternativas consideradas**: los 20 s del prototipo; una consulta sin espera en otra tarea, que es más compleja.

## R-12. Respaldo en un módulo propio (QP-7)

- **Decisión**: `respaldo.py` con `ConsultaDeRespaldo(cliente_pey, repositorio, difusor, reloj)`, que hace la consulta con su intervalo mínimo y la única puerta de "registrar y avisar". `main.py` (ver cobro y aviso de pey) y `canal.py` la reciben ya creada.
- **Por qué**: el canal se prueba solo, con pytest-asyncio, un pey simulado y `RelojFalso`, sin levantar la app.
- **Alternativas consideradas**: dejarla dentro de `crear_app` y pasarle funciones al canal.
