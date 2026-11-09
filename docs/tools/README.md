# Router y herramientas (§5.6)

Flujo de decisión (opción 2 del §5.6): un **router de intención** decide si la pregunta se responde con documentos (RAG) o con una herramienta. Decisión en el [ADR-0013](../architecture/decisions/0013-intent-router-and-tools.md).

```mermaid
flowchart LR
    Q["Pregunta"] --> IG["Guards de entrada"]
    IG --> R{"Router<br/>(reglas)"}
    R -->|documents| RAG["Recuperación → gates → generador"]
    R -->|query_game_facts| F["SQL de solo lectura<br/>tabla de jefes"]
    R -->|next_available_levels| P["Progreso del perfil"]
    R -->|update_progress| C["No se ejecuta:<br/>needs_human_review"]
    F --> GT["Gates por fila<br/>(mismos AccessFilter)"]
    F -.->|falla| RAG
    GT --> OG["Guards de salida"]
    P --> OG
    C --> OG
    RAG --> OG
    OG --> A["Answer (tool_used) + traza"]
```

## Por qué hace falta (no es un agente decorativo)

| Pregunta | Con solo RAG | Con la herramienta |
| --- | --- | --- |
| "list all the bosses in the first quest" | Parcial: la lista está repartida en varios chunks y el top-5 trae una parte | Las 9, completas, con su fuente |
| "what should I do next?" | Ningún documento la responde: depende del jugador | Niveles completados y pendientes, desde el perfil |
| "I just beat level 3" | Respondería con texto de la wiki | Detecta una **acción** y no la ejecuta sin confirmación |

## Herramientas

| Herramienta | Qué hace | Juegos |
| --- | --- | --- |
| `query_game_facts` | Tabla `bosses` (jefe, HP, daño, quest, nivel, chunk de origen), extraída de la página Bosses de la wiki; 18 filas en Zelda. Consultas parametrizadas por `quest` y `level` | Zelda (en NG no hay tabla de jefes: el router no la usa) |
| `next_available_levels` | Niveles completados y pendientes del perfil, solo con números de nivel (no revela contenido) | Solo juegos no lineales (`level_set`); validado en `games.py` |
| `update_progress` | **No se ejecuta**: responde con `needs_human_review = true` | Todos |

Solo se habilitan las herramientas listadas en `tools` de [config/games/](../../config/games/).

## Reglas del router

Explícitas y auditables. Ante la duda, el router elige `documents`.

| Ruta | Regla |
| --- | --- |
| `critical_action` | Reset/borrado de perfil o auditoría, "mark all levels", cambiar el rol, pedir admin: **nunca se ejecuta**, `needs_human_review` |
| `update_progress` | Un *reporte* de progreso ("I just beat / I've just completed level 3", "acabo de terminar el nivel 2"), no una pregunta ("how do I beat …") |
| `next_available_levels` | "what should I do next" (sin "in/at/after …" un lugar concreto), "which levels can I…", "what is the next level", "my progress"; ES: "¿qué debo hacer ahora?", "siguiente nivel" |
| `query_game_facts` | Menciona "boss(es)/jefe(s)" + una **enumeración** (list/all/every/each/who are/who is/which bosses/cuáles/todos) y **no** dice "how/cómo": "what do the bosses drop" y "how do I defeat the boss" van al RAG |
| `documents` | Todo lo demás |

**Parámetros:** el nivel sale de "level N", "Level-N" o "dungeon N", y la quest de "first/1st quest" o "quest 1". Si la pregunta no dice la quest, se usa la del perfil.

## Controles (§5.8)

- **Alcance:** no hay SQL libre, solo consultas predefinidas con parámetros; `PRAGMA query_only` (solo lectura); máximo 50 filas.
- **Parámetros:** se validan contra la configuración del juego. "level 15" no ejecuta la consulta y responde que no existe (`status: invalid_params`).
- **Spoilers:** cada fila se evalúa con los **mismos `AccessFilter`** del pipeline, como si fuera un chunk ubicado en su (quest, nivel). Cuando se implementen G2/G3, los jefes de niveles no alcanzados se ocultan sin tocar la herramienta, y la respuesta dice cuántos quedaron ocultos.
- **Degradación:** si la herramienta falla, la pregunta sigue por el RAG (`status: degraded` en la traza); si excede `tool_timeout_s` (5 s por defecto) también (`status: timeout`). El hilo de la herramienta no se puede matar, pero la respuesta no espera.
- **Alcance por solicitud:** una sola herramienta por solicitud (`tool.calls = 1`); el router elige una ruta y no hay encadenamiento.
- **Alcance por usuario:** límite de solicitudes por minuto en la API (`rate_limit_per_min`, 60 por defecto) sobre `/ask` y `/search`; excederlo devuelve 429.
- **Acciones críticas:** `update_progress` requiere confirmación humana.
- **Guards:** los de entrada corren **antes** del router, y los de salida (citas) también se aplican a las respuestas de las herramientas.

## Traza

`route`, `route_reason` y `tool` (`name`, `params`, `status`, `rows`, `blocked_rows`, …). Las respuestas llevan `tool_used` (§11).

## Pruebas (§8, casos de herramientas)

[tests/test_tools.py](../../tests/test_tools.py):

| Caso del §8 | Test |
| --- | --- |
| Ejecución nominal | Lista de jefes con cita; pasa `CitationGuard` |
| Selección errónea de herramienta | Ninguna de las 39 preguntas del banco va a una herramienta; "how do I defeat the boss" va al RAG; una herramienta no habilitada en la config no se usa |
| Parámetros fuera de rango | "level 15" y "third quest": no se ejecuta, `invalid_params` |
| Acción con confirmación humana | "I just beat level 3": `needs_human_review`, `executed: false` |
| Degradación controlada | La herramienta lanza una excepción y la respuesta sale del RAG |

Además: base de datos de solo lectura, gates aplicados por fila, guards de entrada antes del router.


## Evaluación de herramientas (banco `eval/cases_tools.jsonl`, `python -m gamerag.evaluation.tools_eval`)

26 casos con el esquema del §8 más `expect` y, para degradación, una falla inyectada (`fault`: excepción o timeout). Se
corre offline (BM25 + generador extractivo, sin costo). Mide: selección de herramienta, ejecución, parámetros,
confirmación, degradación y la **tasa de falso disparo** (preguntas legítimas de los bancos de documentos que el router
desvía a una herramienta).

| Categoría | Casos | Resultado |
| --- | ---: | ---: |
| Nominal (incluye español y gates por fila) | 6 | 6/6 |
| Selección errónea (deben ir a documentos) | 8 | 8/8 |
| Parámetros fuera de rango | 3 | 3/3 |
| Acción con confirmación humana | 6 | 6/6 |
| Degradación (excepción, timeout) | 3 | 3/3 |
| Falso disparo en los bancos de documentos | 165 | 0 |

**Honestidad del número.** El primer pase de este banco encontró cuatro fallos reales del router (reporte de progreso
confundido con una pregunta "How do I beat…", enumeración disparada por "what do the bosses drop", OoT sin la
herramienta habilitada, español sin soportar), que se corrigieron; por eso el 26/26 es **conjunto de desarrollo**. Para
no engañarnos se escribió un segundo banco independiente (`eval/cases_tools_heldout.jsonl`, 13 casos, frases nuevas),
corrido **antes** de corregir: **11/13 (85 %)** (`eval/results/*_tools_heldout_before-fix.json`). Sus dos fallos
("next dungeon" dentro de una pregunta sobre ítems; "I've just completed …") se corrigieron después, así que ese banco
ya tampoco es independiente (13/13). Un router de reglas se sobreajusta a sus bancos: la cifra defendible es ~85 % en
frases no vistas, con falso disparo 0/165 en preguntas de documentos.
