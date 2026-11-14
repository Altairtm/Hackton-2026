# PAGO FÁCIL

Cobra con un código QR de **CoDi**, sin comisiones y con transferencia instantánea. Cuando el pago llega, suena y se ve en pantalla.

Proyecto para el **Hackatón México 2026** (pey + AI Builders México + SpaceXAI). Usa CoDi y está integrado con el API de pey.

> PAGO FÁCIL no es un producto oficial de pey ni de Banco de México.

## Cómo funciona

1. El negocio escribe el monto y el concepto en la web de PAGO FÁCIL.
2. El backend pide a pey un cobro CoDi y la pantalla muestra el QR.
3. El cliente lo escanea con la app de su banco y paga desde su cuenta. No necesita descargar nada.
4. pey avisa al backend con un webhook (`codi.qr.payment_received`).
5. La pantalla del negocio suena y muestra "Pago recibido".
6. *(Opcional)* El negocio también puede cobrar y recibir avisos desde un bot de WhatsApp.

## Estructura

| Carpeta | Contenido |
|---|---|
| [`backend/`](backend/) | API en Python (FastAPI): cobros, webhooks de pey, aviso en tiempo real, cupones |
| [`web/`](web/) | Web del negocio como PWA (HTML, CSS, JS): instalable en Android, iPhone y computadora |
| [`docs/`](docs/) | Plan del hackathon, decisiones y guías |

## Organización del trabajo

- **Plan general:** [docs/plan-hackathon.md](docs/plan-hackathon.md)
- **Épicas** por área (Frontend, UX/UI, Backend, Base de datos, Integraciones, Seguridad, DevOps, Producto y entrega). Cada una agrupa sus issues como sub-issues.
- **Milestones** por fecha: M1 Arranque → M2 Cobro CoDi → M3 Extras → M4 Entrega (12 dic).
- **Etiquetas:** `area: …`, `tipo: …`, `prioridad: …` y `opcional`.

## Reglas importantes

Lee [docs/flujo-git-y-secretos.md](docs/flujo-git-y-secretos.md) antes de tu primer commit.

- **Nunca** subas la API key de pey, secretos de webhook ni archivos `.env`. Usa `.env.example` como plantilla.
- Una rama por issue, por ejemplo `feature/12-pantalla-cobro`, y se une con un pull request.
- En pruebas usa solo datos propios o ficticios. Nunca uses CLABEs ni teléfonos de terceros.
