# ADR-0012: Alias de ubicación en el índice y tokens de frase palabra + número

**Estado:** aceptado (2026-11-06).

## Contexto

- **Level ↔ Dungeon:** la wiki titula las mazmorras "Underworld/Quest 1/Dungeon 3"; el juego y los jugadores dicen "Level-3" y "first quest". `direct_04` y `exact_01` fallaban desde la línea base.
- **Al usar la interfaz,** "how do i beat level 1?" devolvía 5 pedazos del walkthrough general. La página de la Dungeon 1 quedaba en el rank 9.
- **Dos causas:**
  1. el nombre "Level" no aparece en la página de la mazmorra;
  2. BM25 es una bolsa de palabras: "level 1" coincide con cualquier texto que tenga "level" y algún "1". Hasta "dungeon 1" falla, porque "Quest **1**/**Dungeon** 3" contiene las dos palabras.
- **Por qué fallaron las reglas de reescritura** ([ADR-0010](0010-query-expansion.md)): cambiar "level" por "dungeon" en la pregunta no evita la segunda causa.

## Decisión

1. **Alias de ubicación en el texto indexado** (BM25 y e5), generados desde los metadatos del chunk: `Level N` si tiene `location.level`, y `<quest> quest` si tiene `location.quest`. Sale de la configuración del juego, no de los casos.
2. **Tokens de frase en BM25:** cada palabra seguida de un número agrega un token unido (`level 1` y `Level-1` → `level_1`; `Stage 2-3` → `stage_2-3`). Se aplica igual a las preguntas y al índice.

## Criterio y medición

El criterio se fijó antes de medir: aceptar solo si (1) el curso no baja, (2) el total no baja y (3) mejora un conjunto de 12 preguntas de niveles **fuera del banco**. Ese conjunto incluye perturbaciones: con y sin "?", "Level-1", "dungeon 1", primera y segunda quest.

Ablación (búsqueda servida: multi-consulta, fusión plana y búsqueda exacta):

| Configuración | Curso (18) | Equipo (8) | Total (36) | MRR | Niveles en el top-5 (fuera del banco) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Antes ([ADR-0011](0011-flat-fusion-exact-dense.md)) | 0.89 | 0.88 | 0.92 | 0.56 | 3/12 |
| Solo tokens de frase | **0.83** | 0.88 | 0.89 | 0.56 | 5/12 |
| Solo alias | 0.89 | 0.88 | 0.92 | 0.64 | 12/12 |
| **Alias + tokens de frase** | **0.94** | 0.88 | **0.94** | **0.68** | **12/12** |

**Lectura:**
- **Los tokens de frase solos empeoran:** `level_1` solo existía en el walkthrough general, así que reforzaba los fragmentos equivocados.
- **Con el alias,** la página de la mazmorra también tiene `level_1` y la coincidencia es exacta. Las dos piezas se complementan.
- **En las preguntas del curso:** Recall@1 pasa de 0.33 a 0.61 y el MRR de 0.55 a 0.76. Se resuelve `direct_04` (rank 11 → 1); `exact_01` mejora (sin aparecer → rank 7), pero sigue fuera del top-5.
- **Ninja Gaiden:** 6 preguntas de control, con ranks idénticos antes y después.

## Costo reconocido

- `extra_02` ("how do i get more hearts?") baja del rank 4 al 5; sin "?" queda en el 7. Las páginas de mazmorras ahora compiten porque sus "Objectives" dicen "Obtain a Heart Container". No son malas respuestas, pero la evidencia del banco exige la página Items.
- Con la pregunta sin "?", el total queda igual que antes (0.92), no mejor. **La invariancia al "?" deja de ser total:** se mantiene en 35 de 36 casos. El test documenta la excepción por nombre, en lugar de ajustar el sistema a ese caso.
- **La elección entre "solo alias" y "alias + frases" usa el banco** (la diferencia son 3 casos del curso). Se elige la combinación porque cada pieza tiene una justificación propia y porque los tokens de frase sin alias no tienen sentido.

## Alternativas consideradas

- **Reescribir la pregunta** (Level → Dungeon). Rechazada en el ADR-0010 (0.89 → 0.78).
- **Reescritura con LLM.** Requiere la API key. No resuelve la bolsa de palabras.
- **Filtrar por ubicación** (`where` de Chroma con `level = N`). Es útil para los gates de spoilers, pero exige extraer el nivel de la pregunta, y eso es un parser aparte.

## Consecuencias

- **Siguen fallando 2 de 36:** `exact_01` (rank 7) y `team_08` "where do i get bombs?" (rank 11).
- **Quest 1 y Quest 2 siguen mezclándose** cuando la pregunta no dice la quest. Eso lo resuelve el gate G2.
- **Cambia `INDEX_TEXT_VERSION`,** así que el índice de Chroma se reconstruye solo la primera vez.
