# Backend — PAGO FÁCIL

API en **Python (FastAPI)**. Es la única parte que habla con pey y la única que conoce la API key.

## Responsabilidades

- Crear cobros CoDi (`POST https://api.pey.mx/codi/qr`) a partir de lo que pide la web.
- Recibir el webhook `codi.qr.payment_received` y verificar su firma (Standard Webhooks).
- Avisar a la web en tiempo real cuando llega un pago (SSE o WebSocket).
- Inicio de sesión del negocio, historial, corte del día y cupones.
- *(Opcional)* Recibir y responder mensajes del bot de WhatsApp.

## Configuración

Copia `.env.example` a `.env` y rellena los valores. El archivo `.env` está ignorado por Git.

La estructura del proyecto y los comandos para correrlo se agregan en el issue "Crear el proyecto FastAPI con estructura base".
