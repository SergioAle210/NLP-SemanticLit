# Resultados

Registro de cada corrida relevante. El detalle completo de cada una, con los candidatos por caso y su score y relevancia, está en `eval/results/`.

## Recuperación: línea base (2026-11-05)

**Configuración:** Zelda · BM25 (`k1 = 1.5`, `b = 0.75`) · chunking `fixed-w225-o30` (153 chunks) · sin gates · 18 casos con respuesta.

Comando: `uv run python -m gamerag.evaluation.retrieval zelda1`. Archivo: `eval/results/2026-11-05_zelda1_bm25-fixed.json`.

| Métrica | Valor | Meta |
| --- | ---: | ---: |
| Recall@1 | 0.33 | — |
| Recall@3 | 0.56 | — |
| **Recall@5** | **0.78** | ≥ 0.80 |
| **MRR** | **0.47** | — |
| Coverage@5 | 0.78 | — |

| Categoría | n | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| Directas | 5 | 0.80 | 0.65 |
| Paráfrasis | 3 | 0.67 | 0.42 |
| Identificadores exactos | 3 | 0.67 | 0.46 |
| Compuestas | 3 | 0.67 | 0.28 |
| Ambiguas | 2 | 1.00 | 0.67 |
| Versión | 2 | 1.00 | 0.23 |

### Diagnóstico de fallos

Se siguió el orden de diagnóstico del curso (tema 08): primero confirmar que existe un chunk con la evidencia (un test lo garantiza para todos los casos) y después ver dónde quedó en el ranking.

| Caso | Rank del primer relevante | Causa | Mejora candidata |
| --- | ---: | --- | --- |
| `direct_04` "item in Level-3 of the first quest" | > 20 | **Desajuste de identificadores:** el usuario dice *Level-3* y *first quest*; la página se titula *Dungeon 3* y *Quest 1*. Los chunks del Walkthrough mencionan todos los niveles y dominan | Normalizar la consulta con alias del dominio (level ↔ dungeon, first ↔ 1st ↔ 1); búsqueda semántica |
| `compound_03` "enter Level-4 in the first quest…" | > 20 | Ídem | Ídem |
| `exact_01` "old man in Level-4 of the first quest" | 19 | Ídem; además, el chunk con la frase está en medio del recorrido de la mazmorra | Ídem + chunking estructural |
| `paraphrase_01` "sail across the sea" | > 20 | **Paráfrasis pura:** ninguna palabra en común con "cross lakes and oceans" | Búsqueda semántica (fase 3) |
| `direct_01` "Which button swings the sword?" (acierto en rank 4) | 4 | **Sin stemming:** "swings" ≠ "swing" | Stemming o búsqueda semántica |

**Mezcla de versiones (casos `version_*`):** aciertan en el top-5 (Recall@5 = 1.0), pero con MRR = 0.23. A la pregunta *"In the first quest, which dungeon has the Ladder?"*, el **top-1 es una mazmorra de la Second Quest** (`underworld-quest-2-dungeon-7`), y el ranking de las dos preguntas (first y second) es casi idéntico. Es la evidencia de que hace falta el filtro de quest (gate G2, [access-control.md](../architecture/access-control.md)).

### Hipótesis para la fase 3

Se verificaron en la sección siguiente.

1. La búsqueda semántica debería recuperar `paraphrase_01` y mejorar `direct_01`.
2. Un alias de identificadores en la config del juego (level ↔ dungeon, first ↔ 1) debería recuperar `direct_04`, `compound_03` y `exact_01`.
3. El filtro de quest debería llevar los casos de versión a MRR ≈ 1.
4. El chunking estructural debería mejorar el MRR de las compuestas.

Cada una se mide por separado (ablación).

## Recuperación: léxica, semántica e híbrida (2026-11-05)

**Configuración:** Zelda · chunking `fixed-w225-o30` · sin gates · 18 casos con respuesta. Para la híbrida, RRF con k = 60 y 20 candidatos por recuperador ([retrieval/semantic.md](../retrieval/semantic.md)).

Comando: `uv run python -m gamerag.evaluation.retrieval zelda1 --retriever {bm25|dense|hybrid} --model {bge-small-en|e5-small-multi}`.

| Variante | Recall@1 | Recall@3 | Recall@5 | MRR | Latencia media |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.33 | 0.56 | **0.78** | 0.47 | 0.2 ms |
| Semántica (bge, inglés) | **0.39** | 0.50 | 0.50 | 0.45 | 21.5 ms |
| Semántica (e5, multilingüe) | 0.33 | 0.50 | 0.50 | 0.44 | 19.6 ms |
| Híbrida (BM25 + bge) | 0.33 | 0.56 | 0.61 | 0.48 | 22.2 ms |
| **Híbrida (BM25 + e5)** | **0.39** | **0.61** | **0.78** | **0.52** | 21.3 ms |

**Rank del primer chunk relevante por caso** (— = fuera del top-20):

| Caso | BM25 | Sem. bge | Sem. e5 | Híb. bge | Híb. e5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `direct_01` "swings the sword" | 4 | **1** | **1** | 2 | 2 |
| `direct_04` "Level-3 first quest" | — | — | — | — | — |
| `paraphrase_01` "sail across the sea" | — | — | — | — | — |
| `paraphrase_02` "hearts refilled" | 4 | 13 | **1** | 12 | 3 |
| `exact_01` "old man Level-4" | 19 | — | 20 | — | **4** |
| `exact_02` "D-4 section 2" | **1** | 12 | 7 | **1** | **1** |
| `exact_03` "name as ZELDA" | 3 | **1** | 13 | **1** | 3 |
| `compound_02` "boss Level-1 and how" | **3** | 13 | 8 | 4 | 4 |
| `ambiguous_01` "dragon boss" | **1** | 15 | **1** | 6 | **1** |
| `version_01` "first quest Ladder" | 4 | — | 13 | 10 | **3** |
| `version_02` "second quest Ladder" | 5 | **1** | 19 | **1** | 6 |

Los casos restantes (`direct_02`, `direct_03`, `direct_05`, `paraphrase_03`, `compound_01`, `ambiguous_02`) aciertan en el top-5 con todas las variantes; `compound_03` falla en el top-5 con todas; solo la semántica e5 lo encuentra dentro del top-20 (rank 13).

### Lectura

- **Con chunking fijo, la búsqueda semántica sola es peor que BM25** (Recall@5 de 0.50 contra 0.78). Es el resultado opuesto al esperado, y se explica por la dilución (ver abajo).
- **Los dos recuperadores se complementan:** la semántica gana en `direct_01` (formas de palabra) y en `paraphrase_02`; BM25 gana en identificadores (`exact_02`, `compound_02`). La híbrida con e5 conserva el Recall@5 de BM25 y mejora el ranking (MRR de 0.47 a 0.52, Recall@1 de 0.33 a 0.39). Su mayor ganancia es `exact_01` (rank 19 → 4).
- **Lo que no resuelve ningún recuperador:**
  - `direct_04` y `compound_03`, por el desajuste Level/Dungeon (requieren alias);
  - la mezcla de quests (requiere el gate G2).
- **El modelo importa más en la híbrida que en la semántica sola:** e5 y bge empatan solos (0.50), pero e5 combina mejor con BM25 (0.78 contra 0.61), porque sus aciertos están en casos distintos a los de BM25.

### Hallazgo: dilución del embedding en chunks fijos

`paraphrase_01` ("How can I sail across the sea?") debía ser el caso fácil para la búsqueda semántica, y falló con todos los modelos. El chunk con la evidencia ("cross lakes and oceans") mezcla **6 secciones** de la página de Items (Ladder, Magic Key, Power Bracelet, Raft, Rings, Shields):

| Modelo | Rank del chunk fijo (mezcla 6 objetos) | Rank si la sección del Raft fuera un chunk propio |
| --- | ---: | ---: |
| bge | 126 | **2** |
| e5 | 62 | **1** |

El embedding de un chunk es una representación de **todo** su contenido: si mezcla seis temas, no se parece a una pregunta sobre uno solo. BM25 solo necesita que el término aparezca, así que el chunking fijo lo perjudica mucho menos.

**Consecuencia para el plan:** el chunking estructural (un chunk por sección o por fila de tabla) pasa a ser el siguiente paso, **antes** de ajustar la búsqueda híbrida o confirmar el modelo. Sin él, la comparación léxica contra semántica no es justa.
