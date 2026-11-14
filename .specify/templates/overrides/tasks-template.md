---
description: "Plantilla de tasks.md para PAGO FÁCIL (en español, pruebas primero, fases cerradas con verificación)"
---

# Tasks: [NOMBRE DE LA FUNCIONALIDAD]

- **Spec**: [spec.md](spec.md), estado: [Aprobada el AAAA-MM-DD]
- **Plan**: [plan.md](plan.md), estado: [Aprobado el AAAA-MM-DD]
- **Fecha**: [AAAA-MM-DD]
- **Estado**: `[Borrador | En QA | Aprobado | F1 en curso (quién) | F1 terminada (quién, fecha) …]`
- **Entrada**: los documentos de `specs/[###-nombre]/`: plan.md, spec.md, research.md, data-model.md, contracts/ y quickstart.md

> **Notas para los comandos de spec-kit.**
> - Cada tarea sigue el formato obligatorio `- [ ] T001 [P] [US1] Descripción con ruta del archivo`.
> - `/speckit-implement` la marca como `[X]` al terminarla.
> - Los detalles van como sub-puntos sangrados debajo de la tarea.
> - `[P]` = se puede hacer en paralelo (otros archivos, sin dependencias pendientes).
> - `[US1]` = historia de la spec a la que pertenece.
> - Las casillas van siempre en listas, nunca en tablas (en las tablas no se ven).

---

## Reglas de ejecución

1. **Las fases van en orden.** Una fase la hace una sola persona o agente. Al empezar lo anota en **Estado** ("F2 en curso (Claude)") y al cerrarla también ("F2 terminada (Claude, AAAA-MM-DD)").
2. **Pruebas primero.** En cada historia se escriben las pruebas, se ven fallar y después se implementa.
3. **Solo se hace la tarea pedida.** Nada de funciones sorpresa, retoques cosméticos ni refactorizaciones fuera de la tarea.
4. **Si el código obliga a cambiar algo**, se anota en el *Registro de implementación* del plan. Si toca una spec aprobada, se presenta como un cambio `C-n`, que Hugo aprueba por separado.
5. **Una fase cierra con tres cosas:**
   - todas las pruebas en verde, en el backend y en la web: `uv run --directory backend pytest -q`, `ruff check`, `ruff format --check` y los comandos de pruebas de la web que defina el plan (pruebas primero en todo, principio V);
   - su sección en `verification-guide.md`;
   - el mensaje de commit sugerido, con formato `tipo(###): descripción en español`.
   - El commit, el push y el pull request los hace Hugo.
6. **Ninguna prueba automática llama al pey real.** Las pruebas con dinero real son de $0.01 y requieren la autorización de Hugo.

## Reparto

| Fase | Quién la hace | Quién la revisa |
|---|---|---|
| F1 | [persona o agente] | [persona o agente] |

## Dependencias externas

| Dependencia | Qué bloquea | Estado |
|---|---|---|
| [Por ejemplo: CoDi activado en el banco de prueba] | [Por ejemplo: la verificación de pago real de F3] | [Pendiente / Listo] |

## Formato de cada tarea

```text
- [ ] T001 [P] [US1] Descripción con la ruta exacta del archivo
  - **RF**: RF-001, RF-002
  - **Dep.**: T000 (o "ninguna")
  - **Hecho cuando**: criterio verificable (prueba que pasa, comando y salida esperada)
```

---

## Fase 1 (F1): Preparación (Setup)

**Propósito**: dejar listo lo que comparten todas las historias.

- [ ] T001 Crear la estructura del proyecto según el plan
  - **RF**: —
  - **Dep.**: ninguna
  - **Hecho cuando**: [criterio]
- [ ] T002 Cierre de F1: pruebas en verde, sección F1 en `verification-guide.md` y commit sugerido

---

## Fase 2 (F2): Base que bloquea (Foundational)

**Propósito**: lo que tiene que existir antes de cualquier historia.

**⚠️ Ninguna historia empieza antes de cerrar esta fase.**

- [ ] T003 [Pieza base con su ruta]
  - **RF**: [RF-00x]
  - **Dep.**: T002
  - **Hecho cuando**: [criterio]
- [ ] T004 Cierre de F2: pruebas en verde, sección F2 en `verification-guide.md` y commit sugerido

---

## Fase 3 (F3): Historia 1 — [Título] (P1) 🎯 MVP

**Objetivo**: [qué entrega esta historia]

**Prueba independiente**: [cómo se comprueba sola]

### Pruebas de la historia 1 (primero, deben fallar antes de implementar)

- [ ] T005 [P] [US1] Prueba de [comportamiento] en `backend/tests/test_[nombre].py` (o en las pruebas de `web/` si la historia es de interfaz)
  - **RF**: [RF-00x]
  - **Dep.**: T004
  - **Hecho cuando**: la prueba existe y falla por la razón esperada

### Implementación de la historia 1

- [ ] T006 [US1] [Implementación] en `backend/app/[archivo].py`
  - **RF**: [RF-00x]
  - **Dep.**: T005
  - **Hecho cuando**: T005 pasa
- [ ] T007 [US1] Cierre de F3: pruebas en verde, sección F3 en `verification-guide.md` y commit sugerido

**Punto de control**: la historia 1 funciona y se puede demostrar sola.

---

## Fase 4 (F4): Historia 2 — [Título] (P2)

[La misma estructura: pruebas primero, implementación y cierre de fase.]

---

## Fase N: Pulido y temas transversales

- [ ] TXXX [P] Documentación: `backend/README.md` y quickstart
- [ ] TXXX Revisión de seguridad: secretos, firma de webhooks, entradas y CORS
- [ ] TXXX Validar `quickstart.md` de punta a punta
- [ ] TXXX Cierre de la fase N: pruebas en verde, guía de verificación y commit sugerido

---

## Dependencias y orden de ejecución

```text
F1 → F2 → F3 (Historia 1, MVP) → F4 (Historia 2) → … → FN (Pulido)
```

- [Qué historias son independientes entre sí y cuáles dependen de otras]
- [Qué tareas `[P]` se pueden hacer a la vez dentro de cada fase]

## Estrategia

1. **MVP primero**: F1, F2 y F3, y después se valida la historia 1 sola antes de seguir.
2. **Entrega incremental**: cada historia suma valor sin romper las anteriores.

## Trazabilidad

| Requisito | Tareas |
|---|---|
| RF-001 | T005, T006 |

## Revisión QA de tasks

| # | Tipo | Hallazgo | Requisitos | Recomendación | Decisión |
|---|---|---|---|---|---|
| QT-1 | [Tipo] | [Con su prueba] | [RF-00x] | [Una sola] | [Decisión de Hugo] |

**Bloques de la pasada:** [una línea por bloque]
