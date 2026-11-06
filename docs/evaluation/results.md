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
  > **Nota posterior:** esta explicación resultó incompleta. En esta corrida, los embeddings indexaban solo el texto del chunk. Al indexar también la ruta de la página, la semántica con chunking fijo sube a 0.78. Ver "Chunking estructural" más abajo.
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

## Recuperación: chunking estructural (2026-11-05)

**Cambios respecto a la corrida anterior:**
1. **Chunking estructural** (`structural-w225-m15`, [ingestion/chunking.md](../ingestion/chunking.md)): 243 chunks, con el 9% mezclando secciones (antes 61%).
2. **Los embeddings indexan lo mismo que BM25:** ruta de la página + texto ([retrieval/semantic.md](../retrieval/semantic.md)). Antes, los embeddings solo veían el texto del chunk. Las variantes con chunking fijo se volvieron a correr con este cambio, para que la comparación entre chunkings sea con la misma configuración.

Archivos: `eval/results/2026-11-06_zelda1_*` (fecha UTC). Los `2026-11-05_*` de las variantes semántica e híbrida son la corrida anterior, sin la ruta de la página.

| Variante | Chunking | Recall@1 | Recall@3 | Recall@5 | MRR |
| --- | --- | ---: | ---: | ---: | ---: |
| BM25 | fijo | 0.33 | 0.56 | 0.78 | 0.47 |
| BM25 | estructural | 0.39 | 0.50 | 0.61 | 0.49 |
| Semántica bge | fijo | 0.50 | 0.67 | 0.78 | 0.61 |
| Semántica bge | estructural | **0.61** | **0.78** | 0.78 | **0.72** |
| Semántica e5 | fijo | 0.44 | 0.61 | 0.72 | 0.57 |
| Semántica e5 | estructural | 0.44 | **0.78** | 0.83 | 0.63 |
| Híbrida bge | fijo | 0.44 | 0.67 | 0.72 | 0.58 |
| Híbrida bge | estructural | 0.44 | **0.78** | 0.83 | 0.62 |
| Híbrida e5 | fijo | 0.33 | 0.67 | 0.78 | 0.53 |
| **Híbrida e5** | **estructural** | 0.33 | 0.72 | **0.89** | 0.55 |

**Rank del primer chunk relevante, con chunking estructural** (— = fuera del top-20):

| Caso | BM25 fijo | BM25 | Sem. bge | Sem. e5 | Híb. bge | Híb. e5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `direct_01` "swings the sword" | 4 | 10 | 1 | 1 | 3 | 2 |
| `direct_02` "Blue Candle cost" | 1 | 5 | 2 | 2 | 2 | 3 |
| `direct_04` "Level-3 first quest" | — | — | 11 | 7 | 17 | 11 |
| `paraphrase_01` "sail across the sea" | — | — | **1** | **1** | 2 | 2 |
| `paraphrase_02` "hearts refilled" | 4 | 1 | 1 | 3 | 1 | 1 |
| `exact_01` "old man Level-4" | 19 | — | — | — | — | — |
| `exact_02` "D-4 section 2" | 1 | 6 | 7 | 7 | 1 | 5 |
| `compound_02` "boss Level-1 and how" | 3 | 17 | 1 | 1 | 4 | 5 |
| `compound_03` "enter Level-4 and item" | — | — | 2 | 2 | 7 | 4 |
| `ambiguous_01` "dragon boss" | 1 | 1 | 6 | 4 | 3 | 2 |
| `version_01` "first quest Ladder" | 4 | 4 | 1 | 2 | 1 | 3 |
| `version_02` "second quest Ladder" | 5 | 1 | 1 | 2 | 1 | 1 |

Los demás casos aciertan en el top-3 con todas las variantes estructurales.

### Lectura

1. **El chunking estructural mejora la búsqueda semántica y empeora BM25.**
   - Semántica bge: MRR de 0.61 a **0.72**, Recall@1 de 0.50 a **0.61**.
   - Semántica e5: Recall@5 de 0.72 a 0.83.
   - BM25: Recall@5 de 0.78 a **0.61**.

   Los dos recuperadores reaccionan de forma opuesta al tamaño del chunk.
2. **La hipótesis de dilución se confirma en la evaluación completa:** `paraphrase_01` ("sail across the sea") pasa de no encontrarse a **rank 1** con la búsqueda semántica.
3. **Corrección de la interpretación anterior:** el 0.50 de la búsqueda semántica con chunking fijo no se debía solo a la dilución. **Indexar la ruta de la página junto con el texto** la sube a 0.78 (bge) con el mismo chunking. La ruta aporta la ubicación ("Underworld/Quest 1/Dungeon 4"), que el texto de muchos chunks no menciona. Los dos efectos son reales; cada uno se midió por separado.
4. **Por qué BM25 empeora:** con chunks más cortos y de tamaños muy variados, varios casos quedan detrás de chunks pequeños que comparten un término. Por ejemplo, en `direct_01` ganan chunks de 26 a 48 palabras con el encabezado "[B Button items > …]", donde "button" coincide con la pregunta. Una prueba de sensibilidad del parámetro de longitud de BM25 (`b` en 0.75, 0.5 y 0.3) **no** recupera el total (Recall@5 entre 0.61 y 0.67), así que no es la causa principal. No se ajustó `b`: elegirlo mirando estos 18 casos sería sobreajustar.
5. **No hay una variante que gane en todas las métricas:**
   - para **Recall@5** (¿está la evidencia entre los 5 chunks que recibirá el LLM?), gana la **híbrida e5 estructural, con 0.89** (16 de 18);
   - para el **orden** (MRR, Recall@1), gana la **semántica bge estructural**.

   Un reranker que reordene los candidatos de la híbrida podría combinar las dos ventajas.
6. **Sigue sin resolverse:** el desajuste "Level-N / first quest" frente a "Dungeon N / Quest 1" (`direct_04`, `exact_01`, en parte `compound_03`) y la mezcla de quests. Requieren el alias de identificadores y el gate G2, no un mejor ranking.

**Cautela estadística:** con 18 casos, cada caso equivale a 0.056 de Recall. La diferencia entre 0.83 y 0.89 es **un caso**. Las conclusiones de dirección (estructural ayuda a la semántica; la híbrida maximiza el recall) son más sólidas que las diferencias puntuales entre variantes cercanas. Ampliar el banco con casos del equipo reduciría esta incertidumbre.

### Decisión

Configuración de recuperación para la fase 3: **híbrida (BM25 + e5) con chunking estructural**, porque maximiza Recall@5, la métrica que determina si el LLM recibe la evidencia ([ADR-0009](../architecture/decisions/0009-phase3-retrieval-config.md)). La línea base (BM25 + fijo) se conserva como referencia.

## Corrección: BM25 devolvía chunks con score 0 (2026-11-06)

La primera prueba de punta a punta del pipeline ([contracts/pipeline.md](../contracts/pipeline.md)) mostró que **BM25 rellenaba el top-k con chunks de score 0** (sin ningún término de la consulta), en el orden del corpus. **RRF los premiaba por aparecer en la lista.** Con los 50 candidatos del pipeline, a "How can I sail across the sea?" le respondía primero la página de controles.

**Corrección:** BM25 solo devuelve chunks con score > 0. Hay un test de regresión (`test_bm25_returns_only_matching_chunks`).

**Efecto en las métricas:** se volvieron a correr las 10 configuraciones (con 20 candidatos, la profundidad de la evaluación). **Solo cambió la híbrida e5 con chunking fijo:**
- `paraphrase_03` pasó del rank 1 al 2;
- Recall@1 pasó de 0.39 a 0.33;
- MRR pasó de 0.56 a 0.53.

Las tablas de arriba ya tienen el valor corregido. **La configuración elegida (híbrida e5 estructural, Recall@5 = 0.89) no cambió.** El efecto era pequeño con 20 candidatos y grande con 50, porque más candidatos dejan entrar más chunks de score 0.

Los resultados de la sección "léxica, semántica e híbrida" (corrida anterior, sin la ruta en los embeddings) se obtuvieron con el bug; se conservan como registro histórico.

## Verificación: lo servido es lo medido (2026-11-06)

El Recall@5 de 0.89 se midió con la híbrida recuperando **20 candidatos por recuperador**. El pipeline pide 50 candidatos (para que los filtros de acceso tengan margen), y la híbrida usaba `max(k, 20)`. Por eso fusionaba listas de 50, y RRF con listas más largas suma puntos a chunks que solo aparecen abajo y cambia el orden de los primeros:

| Profundidad de cada ranking en la fusión | Recall@5 |
| --- | ---: |
| 20 (evaluada) | 0.89 |
| 50 (lo que servía el pipeline) | 0.83 (cae `compound_03`) |

**Corrección:** la profundidad de la fusión es fija (20) e independiente del `k` pedido. **Medición del pipeline completo** (50 candidatos → filtros → top-5 que recibe el generador, perfil `completionist`): la evidencia llega al contexto en **16 de 18 casos (0.89)**. Fallan `direct_04` y `exact_01`, el desajuste Level/Dungeon.

Hay dos tests de regresión:
- el orden de los primeros resultados no depende del `k` pedido;
- el Recall@5 del pipeline servido debe ser ≥ 0.88 (requiere el extra `semantic` y la ingesta estructural; en el CI se salta).

## Robustez: reranker y chunking por fila (2026-11-06)

**Motivación:** al probar la API con preguntas escritas como un jugador ("How can I attack?", "Which button do i have to press to attack?", "How can I atack?"), la respuesta correcta (Controls: `NES: A | Action: Swing the sword`) no aparecía o quedaba abajo. Se agregó la categoría **`robustness`** al banco: **6 casos** de lenguaje coloquial, vago o con errores de tipeo. Ahora `course` designa las 18 preguntas con respuesta de la distribución del curso, y `overall` las 24.

**Hipótesis probadas:**
1. Un **reranker cross-encoder** (lee pregunta y chunk juntos) conectaría "attack" con "swing the sword".
2. El **chunking por fila** (`rows`: cada fila de tabla o celda de mapa es un chunk) evitaría la dilución de la tabla de controles, que tenía 7 botones en un solo chunk.

| Configuración | Recall@5 course (18) | Recall@5 overall (24) | MRR course | Latencia |
| --- | ---: | ---: | ---: | ---: |
| **Híbrida e5, estructural (ADR-0009)** | **0.89** | **0.79** | 0.55 | 20 ms |
| + reranker `minilm-en` | 0.78 | 0.67 | **0.64** | 808 ms |
| + reranker `mminilm-multi` | 0.72 | 0.62 | 0.58 | 2244 ms |
| Híbrida e5, por fila | 0.78 | 0.71 | 0.57 | 22 ms |
| Híbrida e5, por fila + `minilm-en` | 0.72 | 0.62 | 0.57 | 871 ms |
| Semántica e5, por fila | 0.83 | 0.75 | 0.66 | 23 ms |
| BM25, por fila | 0.67 | 0.54 | 0.51 | 0.5 ms |

En robustez, la configuración actual acierta 3 de 6. Ninguna variante resuelve "How can I attack?", "How can I atack?" ni "use my secondary item".

### Lectura

- **Las dos hipótesis se rechazan.**
  - El reranker mejora el orden de lo que ya estaba bien (Recall@1 del curso de 0.33 a 0.50; MRR de 0.55 a 0.64), pero **saca evidencia del top-5** en otros casos y es unas 40 veces más lento en CPU.
  - El chunking por fila deja `NES: A | Action: Swing the sword` como un chunk propio, y aun así "How can I attack?" no lo encuentra.
- **La causa es un desajuste de vocabulario, no la dilución.** El jugador dice *attack*; la wiki dice *swing the sword*. Muchos chunks sí contienen "attack" (enemigos y jefes que atacan) y le ganan a la respuesta. Ocurre lo mismo con *secondary item* ↔ *subweapon*, *menu* ↔ *sub-screen*, y con el caso pendiente desde la línea base, *Level-3* ↔ *Dungeon 3*.
- **El curso propone para este problema la reescritura de la consulta y la recuperación multi-consulta** (tema 08, diapositivas 211 y 212): expresar la consulta con el vocabulario del documento y recuperar con varias formulaciones.
- **No se adopta ninguna de las variantes probadas.** El código queda disponible (`--reranker`, `--chunker rows`) para comparaciones futuras, por ejemplo el reranker como señal de confianza para la abstención.

## Transformación de consultas: ortografía + glosario + multi-consulta (2026-11-06)

**Conjunto independiente del equipo:** se agregaron **8 preguntas con respuesta y 1 sin respuesta** escritas por un integrante como jugador, sin ver el corpus ni el sistema (`author: team`), más 4 propias (`author: assistant`). El evaluador reporta `course` (18), `team` (8) y `overall` (36).

**Antes** (híbrida e5 estructural): curso 0.89, **equipo 0.50**, total 0.72. Las preguntas del equipo rinden mucho peor que las escritas conociendo el corpus, lo que confirma el sesgo del banco original.

**Ablación** de la transformación de consultas ([retrieval/query-expansion.md](../retrieval/query-expansion.md)), Recall@5:

| Componente | Curso (18) | Equipo (8) | Robustez (18) | Total (36) |
| --- | ---: | ---: | ---: | ---: |
| Sin expansión | 0.89 | 0.50 | 0.56 | 0.72 |
| Solo ortografía | 0.89 | 0.50 | 0.56 | 0.72 |
| Solo sinónimos | 0.89 | 0.62 | 0.72 | 0.81 |
| Solo reglas Level/Quest | **0.78** | 0.50 | 0.56 | 0.67 |
| **Ortografía + sinónimos (elegida)** | **0.89** | **0.75** | **0.83** | **0.86** |
| Todo | 0.78 | 0.75 | 0.83 | 0.81 |

**Lectura:**
- **Los sinónimos aportan casi todo.** La ortografía sola no cambia nada, pero combinada con los sinónimos sí: "atack" → "attack" activa la entrada "attack → swing the sword".
- **Las reglas de identificadores perjudican** y se descartan.
- La configuración elegida mejora las preguntas del equipo de 0.50 a 0.75 y el total de 0.72 a 0.86, **sin pérdida en las del curso**.
- **Cautela:** la elección se hizo con este mismo banco, y el glosario se escribió conociendo los fallos. Hace falta una segunda tanda de preguntas del equipo para confirmarlo ([ADR-0010](../architecture/decisions/0010-query-expansion.md)).

Siguen fallando con la configuración elegida:
- `direct_04` y `exact_01` (Level ↔ Dungeon);
- `team_02` "how can i heal?" (rank 9);
- `team_08` "where do i get bombs?" (rank 11);
- `robust_06` "secondary item" (rank 11).

### Preguntas exploratorias y transposición de letras (2026-11-06)

**Preguntas exploratorias.** Se probaron 8 preguntas nuevas de jugador, con el glosario sin cambios. No se agregaron al banco. Las preguntas fueron:
- "how do i use the booomerang?"
- "what can i heal?"
- "how do i get more hearts?"
- "how do i save my game?"
- "who made the game?"
- "how can i atcack?"
- "does the shiled do anything?"
- "how do i beat dungeon 3?"

**Resultado:** en las 8, la evidencia queda en el top-5 del pipeline servido. Dos se parecen a preguntas de la primera tanda (attack y heal), así que la validación es solo parcial.

**Observaciones:**
- **Mezcla de quests:** en "dungeon 3", los ranks 1 y 2 son de la Quest 2 (Dodongos) y la Quest 1 (Manhandla) aparece en los ranks 3 y 5. Esto lo corrige el gate G2, no el ranking.
- **Ruido de la pregunta con errores:** en "atcack", la variante corregida encuentra Controls (rank 3), pero la original aporta ruido en los ranks 1 y 2.
- **Orden:** en 4 de las 8, la evidencia está entre los ranks 3 y 5. Eso afecta al generador extractivo, que responde con el rank 1.
- **Transposición no corregida:** "shiled" no se corregía, porque un intercambio de letras vale 2 en Levenshtein.

**Cambio:** se pasó a Damerau-Levenshtein restringida, donde un intercambio de dos letras vecinas vale 1. Se eligió por el tipo de error (los intercambios son de los errores de tipeo más comunes), sin ajustar nada al banco.

| Medición | Antes | Después |
| --- | --- | --- |
| Preguntas del banco cuya variante cambia | — | 0 de 39 |
| Recall@5 curso / equipo / total | 0.89 / 0.75 / 0.86 | idéntico (los casos también) |
| "does the shiled do anything?" | Shields en el rank 2 | Shields en el rank 1 |
| Correcciones falsas sobre 17,123 palabras válidas | 827 | 832 (+5) |

**Lectura:** el banco no puede medir este cambio, porque ninguna de sus preguntas tiene un intercambio de letras. La evidencia a favor es la pregunta exploratoria y el costo medido (+5 correcciones falsas sobre 17,123 palabras). La prueba de estrés dejó ver algo que ya existía: el corrector cambia el 4.9% de las palabras inglesas válidas que no aparecen en el corpus ([retrieval/query-expansion.md](../retrieval/query-expansion.md)).

### El signo de pregunta, la fusión plana y la búsqueda exacta (2026-11-06)

En la interfaz, "How do i attack" dejaba Controls en el rank 8, y "How do i attack?", en el rank 1. Por etapa:

| Lista | Sin "?" | Con "?" |
| --- | ---: | ---: |
| BM25, pregunta original | — | — |
| e5, pregunta original | 11 | 5 |
| Variante (BM25, e5 e híbrida) | 1 | 1 |
| **Fusión final en dos niveles** | **8** | **1** |

**Causa: la fusión en dos niveles.** La variante encontraba Controls en el rank 1 con los dos recuperadores, pero entraba a la fusión final como un solo voto. Los resultados mediocres de la pregunta original, que aparecían en las dos listas, le ganaban.

**Prueba de perturbación** (todo el banco sin el "?" final; 34 de las 36 preguntas lo tienen):
- con la fusión en dos niveles, el total baja de 0.86 a **0.81** (`robust_01` 5 → 8, `extra_02` 4 → 7);
- con la **fusión plana** (un solo RRF sobre las 4 listas), da **0.92 en las dos formas**.

**Hallazgo secundario: HNSW es aproximado.** Con el mismo código, una corrida dio 0.89 (`extra_04` en el rank 12) y las siguientes 0.92 (rank 4). Se comparó el top-20 de Chroma con el top-20 exacto: en 1 de 3 procesos, una consulta difería. Ahora la búsqueda semántica compara contra todos los chunks del juego y ordena por coseno exacto. Después del cambio coincidió en 5 de 5 corridas, y los números de la tabla no cambian.

Resultados en [ADR-0011](../architecture/decisions/0011-flat-fusion-exact-dense.md). **Configuración servida: curso 0.89, equipo 0.88, total 0.92, MRR 0.56**, invariante al "?". Siguen fallando `direct_04`, `exact_01` y `team_08`.

**Lección:** que la evidencia quede en el top-5 dependía de un signo de puntuación. Las pruebas de perturbación (cambiar algo que no debería importar y verificar que el resultado no cambie) encuentran fragilidad que el banco no ve, porque las preguntas del banco están escritas "bien".

### Level ↔ Dungeon: alias de ubicación y tokens de frase (2026-11-06)

En la interfaz, "how do i beat level 1?" devolvía 5 pedazos del walkthrough general, y la página de la Dungeon 1 quedaba en el rank 9. En pantalla parecían repetidos: eran partes distintas de la misma sección larga ("1st Quest Overview", unas 840 palabras, dividida en 4 chunks). La interfaz ahora muestra el `chunk_id` y el inicio del texto para distinguirlos.

**Causas:**
1. "Level" no aparece en la página de la mazmorra.
2. BM25 es una bolsa de palabras: "level 1" coincide con cualquier texto con "level" y algún "1", y "Quest 1/Dungeon 3" contiene "dungeon" y "1".

**Ablación,** con el criterio fijado antes de medir y 12 preguntas de niveles fuera del banco:

| Configuración | Curso | Equipo | Total | MRR | Niveles (fuera del banco) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Antes | 0.89 | 0.88 | 0.92 | 0.56 | 3/12 |
| Solo tokens de frase | 0.83 | 0.88 | 0.89 | 0.56 | 5/12 |
| Solo alias | 0.89 | 0.88 | 0.92 | 0.64 | 12/12 |
| **Alias + tokens de frase** | **0.94** | 0.88 | **0.94** | **0.68** | **12/12** |

**Resultado:**
- `direct_04` se resuelve (rank 11 → 1) y `exact_01` mejora (sin aparecer → rank 7).
- En el curso, Recall@1 pasa de 0.33 a 0.61.
- Ninja Gaiden no cambia.

**Costo:** `extra_02` baja del rank 4 al 5 (sin "?", al 7), así que la invariancia al "?" se mantiene en 35 de 36 casos. Detalle en el [ADR-0012](../architecture/decisions/0012-location-aliases-phrase-tokens.md).

**Configuración servida: curso 0.94, equipo 0.88, total 0.94, MRR 0.68.** Siguen fallando `exact_01` (rank 7) y `team_08` (rank 11).

### Preguntas de ubicación: "where is…" (2026-11-06, exploratorio)

Se probaron 8 preguntas fuera del banco con la configuración servida. La evidencia se buscó a mano en el corpus.

| Pregunta | Rank de la evidencia | Nota |
| --- | :-: | --- |
| where is the white sword? / where can i buy the blue ring? / where is the raft? / where is the hidden shop? | 1 | Bien |
| where is dungeon 3? | 3 | La Q1 Dungeon 3 dice "entrance… located at E-4 of section 8"; los ranks 1-2 son de la Quest 2 |
| where is the entrance to level 9? | 3 | "find the entrance at Spectacle Rock"; también se mezcla la Q2 |
| where do i find the magical key? | 5 | Arriba salen páginas de la Q2 |
| where is level 1? | 7 | La página de la mazmorra no dice dónde está; el mapa dice "first dungeon" |

**Hallazgos:**
- **La ubicación de las mazmorras está en dos lugares:** al inicio del walkthrough de cada mazmorra y en las páginas del mapa (Hyrule 1-8), por coordenada.
- **Ordinales:** las páginas del mapa usan "first/third/ninth dungeon", no "level N". Es un desajuste de vocabulario nuevo. Posible solución con la misma idea de los alias (first ↔ 1); falta medirla.
- **Mezcla de quests:** cuando la pregunta no dice la quest, salen las dos. La ingesta ya distingue la quest (ruta, `location.quest` y alias), y cuando la pregunta la menciona funciona. Lo que falta está en el perfil del jugador: lo resuelve el **gate G2** (`where` por quest), no la ingesta ni el ranking. Para un jugador de la Q1, ver la Q2 es además spoiler.
- **Notación de la wiki:** "E-4 of section 8" es la cuadrícula del mapa. Explicarla le toca al generador.

### Análisis de abstención

¿Pueden los puntajes de recuperación decidir cuándo abstenerse ("what do i do if ig im stuck", "Hookshot", "horse")? Se compararon dos señales sobre los 39 casos:

| Señal | Preguntas sin respuesta | Preguntas con respuesta (las más bajas) |
| --- | --- | --- |
| Similitud coseno del top-1 (e5) | 0.809 a 0.832 | Desde 0.821 (`paraphrase_01`) |
| Máximo del cross-encoder en el top-5 | −7.5 a −9.9 | Desde −11.2 (`paraphrase_02`) |

**Las distribuciones se superponen:** cualquier umbral que rechace las 3 preguntas sin respuesta también rechaza varias que sí la tienen ("stuck" se parece al corpus más que "sail across the sea"). **La abstención no se puede decidir con los puntajes de recuperación.** Debe decidirla el generador, juzgando si el contexto responde la pregunta (§5.5). Queda como requisito del `HaikuGenerator` ([contracts/generation.md](../contracts/generation.md)).
