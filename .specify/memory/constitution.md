# Constitución de PAGO FÁCIL

PAGO FÁCIL es un punto de venta para negocios pequeños de México (tienditas, ferreterías, tortillerías) que cobra con **CoDi** sin comisión. El negocio escribe el monto. El cliente escanea el QR desde **la app de su banco**. El negocio oye y ve "Pago recibido" en segundos. Usamos el API de pey como integración, y PAGO FÁCIL **no revende** el acceso a ese API.

Esta constitución manda sobre specs, planes, tareas, código y `AGENTS.md`. Si choca con las [reglas oficiales del hackathon](https://hackatonmexico.com/reglas), mandan las reglas.

## Principios fundamentales

### I. El pago se confirma en el servidor (NO NEGOCIABLE)

- Un cobro solo DEBE pasar a *pagado* por una de dos fuentes:
  - un webhook de pey con firma Standard Webhooks válida;
  - una consulta directa del backend al API de pey.
- Nada que venga del navegador, de una captura de pantalla o del cliente PUEDE marcar un cobro como pagado.
- Un webhook sin firma válida DEBE rechazarse sin cambiar ningún dato.

*Por qué:* la demo es pública. Sin esta regla, cualquiera podría hacer sonar la pantalla del negocio por dinero que nunca llegó.

### II. Una orden nunca se ejecuta dos veces (NO NEGOCIABLE)

- Cada pago DEBE procesarse una sola vez, aunque pey reenvíe el webhook o la consulta de respaldo lo vuelva a encontrar.
- La deduplicación DEBE usar el `transactionId` de pey. El `webhook-id` sirve como primera barrera.
- Toda acción que dispare un pago (sonido, aviso, cupón, inventario) DEBE colgar de esa única transición de *pendiente* a *pagado*.

### III. Los secretos nunca salen del backend (NO NEGOCIABLE)

- `PEY_API_KEY`, `PEY_WEBHOOK_SECRET` y cualquier otra credencial solo PUEDEN vivir en `backend/.env` (en local) o en las variables del hosting.
- NUNCA PUEDEN aparecer en código, commits, issues, pull requests, logs, respuestas del API, capturas ni chats.
- La web NUNCA llama a pey directamente.
- Si una llave se filtra, se rota y se avisa a pey en menos de 24 horas, como indica `docs/flujo-git-y-secretos.md`.

### IV. Spec primero y alcance anclado (NO NEGOCIABLE)

- **Orden de aprobación.** Ningún código de producto se escribe sin `spec.md`, `plan.md` y `tasks.md` aprobados en `specs/NNN-<nombre>/`.
- **Aprobar no es empezar.** Aprobar un paso no autoriza el siguiente: el siguiente empieza cuando Hugo lo pide.
- **Solo lo pedido.** Se hacen solo las tareas de `tasks.md`, en su orden. Nada de funciones sorpresa, retoques cosméticos ni refactorizaciones no pedidas.
- **Nunca suponer.** Ante una duda o un caso límite sin definir, el agente se detiene y consulta con opciones.
- **Sin desincronización.** Si el código obliga a cambiar algo, la spec y el plan se actualizan en el momento, en el registro de implementación del plan.
- **Cambios a una spec aprobada.** Se presentan como `C-n`. Hugo los aprueba por separado y se aplican solo cuando él lo pide.

### V. Pruebas primero, en todo (NO NEGOCIABLE)

- En el backend y en la web, cada comportamiento DEBE tener su prueba escrita y vista fallar **antes** de implementarse.
- Las pruebas automáticas NUNCA llaman al pey real ni dependen del reloj real. Usan un pey simulado y un reloj controlado.
- Las pruebas con dinero real son de **$0.01 MXN**. Solo se hacen con cuentas propias o con las CLABEs de prueba que entregó pey, y con la autorización de Hugo en ese momento.
- Los nombres de las pruebas se escriben en español, como el comportamiento que comprueban.
- Una fase no se cierra sin tres cosas: todas las pruebas en verde, su guía de verificación manual y el mensaje de commit sugerido.

### VI. CoDi real, reacción real

- Toda funcionalidad de cobro DEBE demostrarse con un **cobro CoDi real** creado con el API de pey en producción.
- También DEBE demostrarse la **reacción visible del sistema al resultado** de ese cobro.
- Las reglas del hackathon no aceptan simularlo.

### VII. Pensado para el mostrador

- Cada pantalla y cada respuesta del API se diseña para un negocio pequeño, con un celular y sin capacitación: monto grande, QR grande, sonido claro.
- El cliente paga **desde la app de su banco, en la opción CoDi**. La cámara normal del teléfono no paga el QR, así que la interfaz SIEMPRE lo indica.
- Todo lo que el usuario toca responde al instante, con estado de carga, de error y de éxito.
- La interfaz funciona desde 320 px de ancho.
- Los mensajes de error se escriben para el dueño del negocio, no para un programador.

### VIII. Un pago no prueba identidad ni entrega

- "Pagado" significa que el dinero llegó a la cuenta. No identifica al cliente ni confirma la entrega.
- Toda spec con cobros DEBE definir qué pasa con:
  - los **pagos tardíos** (después de vencer el QR);
  - los **montos distintos** al pedido;
  - las **fallas** de pey o del webhook;
  - las **devoluciones**.
- El sistema NUNCA pierde un pago. Si llega dinero de un cobro conocido, se registra aunque llegue tarde o sea por otro monto, y se avisa.

### IX. Lo más simple que gane la demo

- Primero se construye el recorrido completo más corto (cobro → QR → pago → aviso). Los extras vienen después.
- No se agrega una pieza (base de datos, cola, framework de frontend, servicio externo) hasta que una spec la justifique.
- Una librería o herramienta nueva requiere una comparativa: opción A frente a B, ventajas, desventajas, curva de aprendizaje y recomendación. Decide Hugo.
- Cada limitación aceptada se escribe en la spec, con el issue que la resolverá.

### X. Si no se ve, no existe

- Cada interacción con pey y cada webhook DEBE dejar un registro (log) con el identificador del cobro y el `requestId` de pey.
- Ese registro NUNCA incluye secretos ni datos bancarios.
- `GET /salud` indica si el backend tiene configuradas sus credenciales, sin mostrar sus valores.
- Antes de culpar a pey, se revisan el historial de webhooks de su portal y nuestros logs.

## Restricciones técnicas e idioma

| Tema | Decisión |
|---|---|
| Backend | Python 3.11+, FastAPI, `httpx`, `pydantic-settings`, `standardwebhooks` |
| Herramientas | `uv` para dependencias, `ruff` para formato y lint, `pytest` para pruebas |
| Web | PWA con HTML, CSS y JavaScript, sin framework, pensada primero para celular |
| Tiempo real | Server-Sent Events, con consulta del estado como respaldo |
| API de pey | `https://api.pey.mx`, autenticación `Bearer`, montos en MXN. No hay ambiente de pruebas: se prueba en producción con $0.01 |
| Apps nativas | Ninguna durante el hackathon: la demo es un enlace |
| Specs | spec-kit (`specify` 1.4.0) con plantillas en español en `.specify/templates/overrides/` |

**Idioma** (decisión de Hugo del 2026-11-14):

- **Nombres del código en español**: variables, funciones, clases, módulos, archivos, rutas del API y campos JSON. Ejemplos: `crear_cobro`, `RepositorioCobros`, `/api/cobros`, `monto`.
- Los nombres que imponen las librerías, los protocolos o pey se dejan como son. Ejemplos: `lifespan`, `codiQrId`, `webhook-id`.
- **También en español**: comentarios, docstrings, nombres de pruebas, specs, planes, guías, mensajes de commit, mensajes para el usuario y explicaciones al equipo.

## Flujo de desarrollo y calidad

1. **Flujo de cada funcionalidad.** Cada paso se aprueba antes de pasar al siguiente:

   ```text
   /speckit-specify → /entrevista-spec → (/speckit-clarify) → /qa-spec NNN
   → /speckit-plan → /qa-spec NNN plan → /speckit-tasks → /speckit-analyze
   → /qa-spec NNN tasks → /speckit-implement por fases → /speckit-converge
   ```

2. **Entrevistas y QA.** Las preguntas se hacen una por una, con opciones y la recomendada primero.
   - Cada QA es de **una sola pasada**.
   - Lo que aparezca después se resuelve como `DP-n` (decisión del plan) o `TK-n` (registro de implementación), no como una ronda nueva de preguntas.
3. **Requisitos.** Se escriben en notación EARS (`RF-###`), con criterios de éxito medibles (`CE-###`) y la sección "Fuera de alcance" obligatoria.
4. **Git para agentes de IA.** Solo lectura: `git status`, `git diff`, `git log` y `git show`.
   - El agente sugiere el mensaje de commit con el formato `tipo(NNN): descripción en español`.
   - Hugo hace el commit, el push y el pull request.
   - Las personas del equipo siguen `docs/flujo-git-y-secretos.md`: una rama por issue y pull request revisado por otra persona.
5. **Rol del agente: mentoría breve.** El agente explica en pocas líneas el porqué de cada decisión técnica. Al cerrar cada fase entrega una guía de verificación manual paso a paso, para que todo el equipo entienda y pueda comprobar el trabajo.
6. **Seguridad antes de cerrar una spec.** Se revisan:
   - que los secretos estén fuera del repo y del cliente;
   - la firma de los webhooks;
   - la validación de entradas en el servidor;
   - CORS y el límite de peticiones de la demo pública.

## Gobierno

- **Prioridad.** Esta constitución manda sobre cualquier otra práctica del proyecto. `AGENTS.md` es su guía operativa para los agentes y DEBE mantenerse sincronizada con ella.
- **Aprobaciones.** Hugo aprueba specs, planes y tasks, y decide los hallazgos de las entrevistas y las QA.
- **Enmiendas.** La constitución solo cambia por un **pull request** que cumpla tres condiciones:
  - Hugo lo propone o lo aprueba;
  - lo revisa al menos otra persona del equipo (Profesor, Altairtm o Miguel);
  - explica el motivo del cambio.
  - Los principios marcados como NO NEGOCIABLE solo cambian si cambian las reglas del hackathon o las condiciones del API de pey.
- **Versionado semántico.**
  - Versión **mayor**: se retira o se redefine un principio.
  - Versión **menor**: se agrega un principio o una sección, o se amplía de forma importante.
  - **Parche**: cambios de redacción.
- **Cumplimiento.**
  - Cada plan llena su verificación de la constitución (*Constitution Check*) antes y después del diseño.
  - Cada QA y cada revisión de un pull request comprueban esta constitución, no solo que el código funcione.
  - Toda excepción se justifica en el seguimiento de complejidad (*Complexity Tracking*) del plan.

**Versión**: 1.0.0 | **Ratificada**: 2026-11-14 | **Última enmienda**: 2026-11-14
