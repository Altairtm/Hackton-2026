# Plan: [NOMBRE DE LA FUNCIONALIDAD]

- **Rama**: `[feature/<issue>-<descripcion>]`
- **Fecha**: [AAAA-MM-DD]
- **Spec**: [spec.md](spec.md), estado: [Aprobada el AAAA-MM-DD]
- **Estado del plan**: `[Borrador | En QA | Aprobado]`
- **Entrada**: la spec de `specs/[###-nombre]/spec.md`

> **Notas para los comandos de spec-kit.**
> - `[NECESITA ACLARACIÓN: …]` equivale a *NEEDS CLARIFICATION*.
> - Los títulos marcados entre paréntesis (*Technical Context*, *Constitution Check*, *Project Structure*, *Complexity Tracking*) son las secciones que espera `/speckit-plan`.
> - El plan se escribe en español.
> - El plan dice **CÓMO**. Cada pieza cita los RF de la spec que cumple.

---

## 0. Resumen

[El requisito principal de la spec y el enfoque técnico, en un párrafo.]

### 0.1 Hechos del código y de las fuentes

[Lo que ya existe y condiciona el diseño, con evidencia. Ejemplos: un endpoint de pey, un archivo del prototipo, un límite de la API.]

| # | Hecho | Evidencia |
|---|---|---|
| H-1 | [Hecho] | [Archivo y línea, documentación de pey o prueba] |

---

## 1. Contexto técnico (Technical Context)

- **Lenguaje y versión**: [por ejemplo Python 3.11+] o [NECESITA ACLARACIÓN]
- **Dependencias principales**: [por ejemplo FastAPI, httpx, standardwebhooks] o [NECESITA ACLARACIÓN]
- **Almacenamiento**: [por ejemplo memoria, SQLite o PostgreSQL] o [NECESITA ACLARACIÓN]
- **Pruebas**: [por ejemplo pytest con pey simulado] o [NECESITA ACLARACIÓN]
- **Plataforma de destino**: [por ejemplo backend en Render o Railway, PWA en el celular del negocio] o [NECESITA ACLARACIÓN]
- **Tipo de proyecto**: [servicio web y PWA] o [NECESITA ACLARACIÓN]
- **Metas de rendimiento**: [con número, por ejemplo "QR en menos de 3 s"] o [NECESITA ACLARACIÓN]
- **Restricciones**: [por ejemplo "un solo proceso", "API key solo en el backend"] o [NECESITA ACLARACIÓN]
- **Escala**: [por ejemplo "un negocio de demo, decenas de cobros al día"] o [NECESITA ACLARACIÓN]

---

## 2. Verificación de la constitución (Constitution Check)

*Puerta de paso: se revisa antes de la investigación (Fase 0) y otra vez después del diseño (Fase 1).*

| Principio de la constitución | Cómo lo cumple este plan | Estado |
|---|---|---|
| [I. …] | [Explicación] | [Cumple / Excepción justificada en §12] |

---

## 3. Estructura del proyecto (Project Structure)

### 3.1 Documentación de esta funcionalidad

```text
specs/[###-nombre]/
├── spec.md               # Qué y por qué (entrevista y QA incluidas)
├── plan.md               # Este archivo (/speckit-plan)
├── research.md           # Fase 0: decisiones investigadas (/speckit-plan)
├── data-model.md         # Fase 1: entidades, estados y validaciones (/speckit-plan)
├── contracts/            # Fase 1: un contrato por interfaz expuesta (/speckit-plan)
├── quickstart.md         # Fase 1: guía para comprobar de punta a punta (/speckit-plan)
├── tasks.md              # Lista de tareas por fase (/speckit-tasks)
└── verification-guide.md # Verificación manual de cada fase (al cerrar cada fase)
```

### 3.2 Código fuente (raíz del repositorio)

```text
backend/
├── app/          # [módulos que toca este plan]
├── scripts/
└── tests/
web/
```

**Decisión de estructura**: [qué carpetas y archivos se crean o cambian, y por qué]

---

## 4. Módulos y piezas con comportamiento

| Pieza | Responsabilidad | Requisitos |
|---|---|---|
| [módulo o archivo] | [qué hace] | [RF-00x] |

---

## 5. Contratos

Cada interfaz expuesta (endpoint, evento SSE, webhook recibido o comando CLI) tiene su archivo `contracts/<nombre>.md` con este formato:

1. **Método y ruta**, o el nombre del evento o comando, y su **propósito**.
2. **Requisitos** que cubre (RF).
3. **Petición**: tabla `Campo | Tipo | Obligatorio | Validación | Requisitos`.
4. **Respuestas por código** (201, 400, 401, 404, 422, 429, 502, 503…): cuándo ocurre cada una y su cuerpo, en una tabla `Campo | Tipo | Requisitos`.
5. **Ejemplo** de petición y de respuesta en JSON, con datos ficticios.
6. **Notas de seguridad**: autenticación, firma, límites y qué nunca se devuelve.

| Contrato | Archivo | Requisitos |
|---|---|---|
| [POST /api/…] | [contracts/….md] | [RF-00x] |

---

## 6. Modelo de datos

El detalle va en [data-model.md](data-model.md): entidades, campos, estados y transiciones, y reglas de validación sacadas de los RF. Aquí va solo el resumen.

---

## 7. Estrategia de pruebas

- **Pruebas primero**: cada tarea de implementación tiene antes su prueba, que se ve fallar y después pasa.
- **Pruebas automáticas**: nunca llaman al pey real; usan un pey simulado.
- **Pruebas reales**: solo con $0.01 y con autorización de Hugo.
- **Nombres de las pruebas** en español, como la spec que comprueban (por ejemplo `test_un_webhook_sin_firma_se_rechaza`).

| Requisito | Prueba | Tipo (unitaria / integración / manual) |
|---|---|---|
| [RF-00x] | [nombre de la prueba o paso manual] | [tipo] |

---

## 8. Plan de implementación

| Fase | Fechas | Quién | Qué | Depende de |
|---|---|---|---|---|
| F1 | [fecha] | [persona o agente] | [resumen] | — |

---

## 9. Decisiones

### 9.1 Decisiones del plan

| # | Decisión | Por qué | Alternativas descartadas |
|---|---|---|---|
| DP-1 | [Decisión] | [Motivo] | [Opción B y por qué no] |

### 9.2 Decisiones de Hugo

[Las que eligió Hugo entre una opción A y una B, con su fecha.]

### 9.3 Revisión QA del plan

| # | Tipo | Hallazgo | Requisitos | Recomendación | Decisión |
|---|---|---|---|---|---|
| QP-1 | [Tipo] | [Con su prueba] | [RF-00x] | [Una sola] | [Decisión de Hugo] |

**Bloques de la pasada:** [una línea por bloque]

---

## 10. Seguridad

- **Secretos**: dónde viven y cómo se comprueba que no salen del backend.
- **Firma de webhooks**: cómo se verifica y qué pasa si falla.
- **Entradas**: qué se valida en el servidor y con qué límites.
- **Abuso de la demo pública**: límites por IP y CORS.

---

## 11. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| [Riesgo] | [Qué rompe] | [Qué hacemos] |

---

## 12. Seguimiento de complejidad (Complexity Tracking)

> Se llena **solo** si la verificación de la constitución tiene excepciones que hay que justificar.

| Excepción | Por qué hace falta | Alternativa más simple descartada y por qué |
|---|---|---|
| [Excepción] | [Necesidad] | [Motivo] |

---

## 13. Aprobación

- [ ] Plan revisado con `/qa-spec [###] plan` y todos los hallazgos QP decididos.
- [ ] Aprobado por Hugo el [AAAA-MM-DD]. Aprobar no autoriza a empezar `tasks.md`: se espera a que Hugo lo pida.

---

## 14. Registro de implementación

[Cada desviación durante la implementación: tareas que cambian, decisiones nuevas, correcciones al revisar y resultados de pruebas.]

| # | Fecha | Qué | Por qué | Afecta |
|---|---|---|---|---|
| TK-1 | [AAAA-MM-DD] | [Cambio] | [Motivo] | [RF, tarea o archivo] |
