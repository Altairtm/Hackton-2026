# Spec [###]: [NOMBRE DE LA FUNCIONALIDAD]

- **ID**: `[###-nombre-funcionalidad]`
- **Fecha**: `[AAAA-MM-DD]`
- **Estado**: `[Borrador | En entrevista | En QA | Aprobada]`. Una línea en prosa: quién la redactó, qué se decidió y qué falta aplicar.
- **Rama**: `[feature/<issue>-<descripcion>]`
- **Issues**: [#n, #m]
- **Entrada**: "$ARGUMENTS"

> **Notas para los comandos de spec-kit.**
> - `RF-###` equivale a *Functional Requirement* (FR-###).
> - `CE-###` equivale a *Success Criterion* (SC-###).
> - `[NECESITA ACLARACIÓN: …]` equivale a *NEEDS CLARIFICATION*.
>
> La spec describe **QUÉ** y **POR QUÉ**. Están prohibidos el stack, la arquitectura, los nombres de archivos, los esquemas de datos, los algoritmos y las firmas de funciones: eso va en `plan.md` y `tasks.md`. Toda la spec se escribe en español.

---

## 1. Contexto y propósito (por qué)

[Qué problema resuelve para el negocio o el cliente que paga, y qué valor aporta dentro de PAGO FÁCIL. Sin detalles técnicos.]

### 1.1 Glosario

| Término | Significado en esta spec |
|---|---|
| [Cobro] | [Lo que el negocio pide a su cliente por un monto] |

---

## 2. Escenarios de usuario y pruebas *(obligatorio)*

[Historias ordenadas por importancia. Cada una se puede construir, probar y demostrar **sola**: si solo se hiciera esa historia, ya habría algo útil que enseñar.]

### Historia 1 — [Título breve] (Prioridad: P1)

**Como** [rol], **quiero** [acción], **para** [beneficio].

**Por qué esta prioridad:** [qué valor aporta y por qué va antes que las demás]

**Prueba independiente:** [cómo se comprueba sola, por ejemplo: "crear un cobro de $0.01 y escanearlo desde la app de un banco con CoDi activado"]

**Escenarios de aceptación:**

1. **Dado** [estado inicial], **cuando** [acción], **entonces** [resultado observable].
2. **Dado** [estado inicial], **cuando** [acción], **entonces** [resultado observable].

---

### Historia 2 — [Título breve] (Prioridad: P2)

**Como** [rol], **quiero** [acción], **para** [beneficio].

**Por qué esta prioridad:** [explicación]

**Prueba independiente:** [explicación]

**Escenarios de aceptación:**

1. **Dado** [estado inicial], **cuando** [acción], **entonces** [resultado observable].

---

[Agrega más historias si hacen falta, cada una con su prioridad.]

---

## 3. Requisitos *(obligatorio)*

### 3.1 Requisitos funcionales (notación EARS)

Cada requisito usa **uno solo** de los cinco patrones EARS, se puede verificar sin ambigüedad y describe un solo comportamiento. Si necesita un "y" para unir dos comportamientos, son dos requisitos. No se admiten adjetivos sin umbral: "rápido", "intuitivo" o "robusto" no son requisitos.

| Patrón | Forma | Cuándo se usa |
|---|---|---|
| Ubicuo | EL SISTEMA \<hará\> | siempre es cierto |
| Dirigido por evento | CUANDO \<disparador\>, EL SISTEMA \<hará\> | responde a algo |
| Estado | MIENTRAS \<estado\>, EL SISTEMA \<hará\> | durante una condición |
| Opcional | DONDE \<característica\>, EL SISTEMA \<hará\> | solo si está presente |
| No deseado | SI \<condición\>, ENTONCES EL SISTEMA \<hará\> | errores y casos límite |

**[Grupo, por ejemplo "Crear cobro"]**

- **RF-001** (Ubicuo): EL SISTEMA [propiedad que siempre se cumple].
- **RF-002** (Dirigido por evento): CUANDO [disparador], EL SISTEMA [respuesta].
- **RF-003** (No deseado): SI [condición de error], ENTONCES EL SISTEMA [manejo y mensaje].
- **RF-004** (Estado): MIENTRAS [estado], EL SISTEMA [comportamiento]. [NECESITA ACLARACIÓN: pregunta concreta]

### 3.2 Entidades clave *(si la funcionalidad maneja datos)*

- **[Entidad]**: [qué representa y sus atributos clave, sin tipos ni esquemas]

---

## 4. Casos límite y manejo de errores

[Por la constitución, toda spec con cobros responde estas preguntas: qué pasa con un **pago tardío**, con un **monto distinto** al pedido, con las **fallas** de pey o del webhook, y con las **devoluciones**.]

| Caso | Comportamiento esperado | Requisitos |
|---|---|---|
| [Caso] | [Qué ve o recibe el usuario] | [RF-00x] |

---

## 5. Fuera de alcance *(obligatorio)*

[Lo que **no** se construye en esta spec, para que la funcionalidad no crezca sola.]

| Fuera de alcance | Dónde se resuelve |
|---|---|
| [Elemento] | [Issue #n o spec futura] |

---

## 6. Criterios de éxito *(obligatorio)*

[Medibles y sin tecnología: se comprueban con un número, un tiempo o una prueba concreta.]

- **CE-001**: [Por ejemplo: "un cobro real de $0.01 se paga desde la app del banco y la pantalla muestra 'Pago recibido' de punta a punta"]
- **CE-002**: [Por ejemplo: "la página recibe el aviso de pago en menos de 2 segundos después de que pey entrega el webhook"]

---

## 7. Supuestos

- [Lo que se da por cierto sin haberlo comprobado, y quién lo confirma]

---

## 8. Dudas y decisiones

### 8.1 Entrevista con Hugo ([AAAA-MM-DD])

| # | Duda | Decisión | Requisitos |
|---|---|---|---|
| E-1 | [Pregunta] | [Respuesta de Hugo] | [RF-00x] |

### 8.2 Cambios a otras specs

| # | Spec | Cambio propuesto | Origen | Estado |
|---|---|---|---|---|
| C-[n] | [###] | [Qué cambia] | [E-n / QA-n] | [Propuesto · Aprobado sin aplicar · Aplicado] |

### 8.3 Propuestas

| # | Propuesta | Por qué | Decisión |
|---|---|---|---|
| P-1 | [Propuesta] | [Motivo] | [Pendiente / Aceptada / Rechazada] |

### 8.4 Revisión QA

| # | Tipo | Hallazgo | Requisitos | Recomendación | Decisión |
|---|---|---|---|---|---|
| QA-1 | [Contradicción · Hueco · Ambigüedad · Promesa imposible · Caso límite · API de pey · Seguridad · Errata] | [Con su prueba] | [RF-00x] | [Una sola] | [Decisión de Hugo] |

**Bloques de la pasada:** [una línea por bloque con lo que se comprobó]

**Erratas:** [lista; se corrigen cuando Hugo lo pida]

### 8.5 Pendientes

- `[NECESITA ACLARACIÓN: pregunta concreta]`

---

## 9. Criterios de finalización

- [ ] Cada RF tiene al menos una prueba automática o un paso de verificación manual.
- [ ] Todos los criterios de éxito (CE) están comprobados.
- [ ] No quedan marcas `[NECESITA ACLARACIÓN]` abiertas.
- [ ] Hay una revisión de seguridad hecha: secretos, firma de webhooks y validación de entradas.
