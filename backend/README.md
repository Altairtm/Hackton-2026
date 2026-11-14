# Backend — PAGO FÁCIL

API en **Python (FastAPI)**. Es la única parte que habla con pey y la única que conoce la API key.

## Arranque

Necesitas [uv](https://docs.astral.sh/uv/). Desde `backend/`:

```bash
cp .env.example .env          # y pon tu PEY_API_KEY dentro; .env está ignorado por Git
uv sync                       # instala dependencias
uv run uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/salud` responde `{"estado": "ok", ...}` e indica si la API key y el secreto del webhook están cargados (nunca muestra sus valores).

## Probar la conexión con pey

Crea un cobro CoDi **real** de $0.01 y guarda el QR en `.tmp/qr-prueba.png`:

```bash
uv run python scripts/probar_pey.py --esperar
```

Escanea la imagen con la app de tu banco. Con `--esperar`, el script consulta a pey hasta ver el pago, así que funciona sin webhook ni URL pública. El dinero enviado a la CLABE de prueba de pey no se devuelve: usa solo $0.01.

## Contrato con la web

| Método y ruta | Qué hace |
|---|---|
| `POST /api/cobros` | Cuerpo `{"monto": 150, "concepto": "Tacos"}`. Crea el cobro en pey y responde `201` con el cobro. |
| `GET /api/cobros/{id}` | Estado del cobro. Si sigue pendiente, pregunta a pey (respaldo del webhook). |
| `GET /api/cobros/{id}/eventos` | Server-Sent Events. Emite `pagado` o `vencido` con el cobro como dato. |
| `POST /webhooks/pey` | Solo para pey. Verifica la firma (Standard Webhooks) y marca el cobro pagado. |
| `GET /salud` | Comprobación de vida. |

Un cobro se ve así:

```json
{
  "id": "W4O9ulAq4Px1",
  "codiQrId": "35f8361d2b",
  "monto": 150.0,
  "concepto": "Tacos",
  "estado": "pendiente",
  "qr": "{\"TYP\":20,...}",
  "qrImagen": "iVBORw0KGgo...",
  "creado_en": 1794677511,
  "expira_en": 1794678111,
  "pagado_en": null
}
```

- `estado`: `pendiente`, `pagado` o `vencido`.
- `qrImagen`: PNG en base64 (`<img src="data:image/png;base64,...">`). Puede ser `null`; en ese caso la web dibuja el QR a partir de `qr`.
- Errores: `422` monto o concepto inválido, `429` demasiados cobros desde la misma IP, `502`/`503` pey falló (el campo `detail` trae un mensaje para mostrar).

En la web:

```js
const eventos = new EventSource(`${API}/api/cobros/${cobro.id}/eventos`);
eventos.addEventListener("pagado", (e) => mostrarPagoRecibido(JSON.parse(e.data)));
```

## Reglas que cumple

- La API key solo se lee de `PEY_API_KEY`; no aparece en el código, en respuestas ni en logs.
- Un webhook sin firma válida se rechaza con `401` y no cambia ningún cobro.
- El mismo pago no se procesa dos veces (se deduplica por `webhook-id` y por `transactionId`).
- Monto mayor a 0, con máximo 2 decimales y tope de `MONTO_MAXIMO` (100 por defecto).
- CORS limitado a `WEB_ORIGIN` (varios orígenes separados por coma).

## Límites del MVP

- Los cobros viven **en memoria**: se pierden al reiniciar el servidor. La base de datos llega en el issue #23.
- Un solo negocio de demo, sin inicio de sesión.
- El límite por IP y el aviso en tiempo real suponen **un solo proceso** (no usar varios workers).

## Calidad

```bash
uv run pytest          # pruebas con un pey simulado; no usan la API key
uv run ruff check .
uv run ruff format .
```
