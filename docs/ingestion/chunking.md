# Chunking

Implementación: [src/gamerag/ingest/sections.py](../../src/gamerag/ingest/sections.py) y [chunking.py](../../src/gamerag/ingest/chunking.py). Decisión: [ADR-0006](../architecture/decisions/0006-fixed-chunking-baseline.md).

## Secciones

El texto limpio se divide por sus encabezados (`== A ==`, `=== B ===`). Cada sección conserva su **ruta jerárquica** (p. ej. `Objectives > Dungeon Walkthrough`). El texto anterior al primer encabezado es la sección `(intro)`. Las secciones sin texto propio no se emiten, pero su título queda en la ruta de las subsecciones.

La ruta sigue la estructura que eligieron los autores de la wiki. Por ejemplo, en las mazmorras de Zelda, "Dungeon Walkthrough" cuelga de "Objectives".

## Línea base: ventana fija (`fixed-w225-o30`)

| Parámetro | Valor | Motivo |
| --- | --- | --- |
| Tamaño | 225 palabras | Aprox. 300 tokens: cabe varias veces en el contexto del LLM y mantiene el tema |
| Solapamiento | 30 palabras (13%) | Evita que una idea quede partida sin contexto en ambos lados |
| Unidad | Palabras | Independiente del tokenizador (todavía no decidido) |
| Límite | La página | La página es la unidad de cita; un chunk nunca mezcla fuentes |
| Secciones | Se ignoran | A propósito: es la línea base del chunking estructural |

**Detalles:**
- El título de cada sección se antepone como `[Ruta > De > Sección]`. Le da contexto al lector y términos a BM25.
- Los saltos de línea se conservan, para que las filas de tablas y las listas sigan siendo legibles. Solo las palabras cuentan para el tamaño.
- Cada chunk registra la sección donde empieza (`section`, `page`) y todas las que abarca (`sections`).

## Limitaciones medidas (motivan la fase 3)

- **El 61% de los chunks de Zelda (94 de 153) y el 46% de los de Ninja Gaiden (32 de 70) cruzan más de una sección.** Un chunk puede mezclar, por ejemplo, el final del recorrido de una mazmorra con su jefe.
- Muchos chunks empiezan a mitad de una frase, por el paso fijo de la ventana.
- Un chunk que cruza secciones hereda la ubicación de la primera. En Ninja Gaiden, eso puede mezclar dos etapas o la pelea con la escena posterior al jefe. No afecta a la línea base, que no tiene gates, pero lo impide la fase 3.

## Chunking estructural (`structural-w225-m15`, fase 3)

Es la configuración elegida para la fase 3 ([ADR-0009](../architecture/decisions/0009-phase3-retrieval-config.md)). Se generó con `--chunker structural`.

| Regla | Valor | Motivo |
| --- | --- | --- |
| Unidad | **Una sección** (o parte de una) | Cada chunk trata un solo tema: evita la dilución del embedding |
| Secciones largas | Se dividen **empaquetando líneas completas** (filas de tabla, ítems, párrafos) hasta 225 palabras; el encabezado se repite en cada parte | Nunca se parte una fila ni una idea. La línea más larga del corpus tiene 185 palabras; si alguna superara el máximo, se partiría por palabras |
| Secciones diminutas | Menos de **15 palabras** → se unen a la siguiente de la página, si el total cabe en 225 | Evita chunks sin contexto como "[Prerequisites] Raft." El umbral es bajo a propósito: unir secciones de temas distintos reintroduce la dilución. Por ejemplo, la sección del Raft (24 palabras) queda sola |
| Solapamiento | Ninguno | Los cortes caen en límites de línea, así que no parten ideas, y el encabezado de sección da el contexto |
| Encabezado | `[Ruta > De > Sección]` por cada sección incluida | Contexto para el lector y términos para la búsqueda |

**Resultado medido:**

| | Fijo | Estructural |
| --- | ---: | ---: |
| Chunks (Zelda / NG) | 153 / 70 | 243 / 84 |
| Palabras por chunk, media (Zelda) | 201 | 110 |
| Chunks que mezclan secciones (Zelda / NG) | **61% / 46%** | **9% / 0%** |

El 9% restante son las secciones diminutas unidas a la siguiente (p. ej. "Enemy drops > Heart" con "Enemy drops > Rupees").

**Efecto en la recuperación** ([evaluation/results.md](../evaluation/results.md)):
- **Mejora la búsqueda semántica:** "sail across the sea" pasa a rank 1; MRR de bge de 0.61 a 0.72.
- **Empeora BM25:** Recall@5 de 0.78 a 0.61.
- La híbrida e5 alcanza **Recall@5 = 0.89**.

## Pendiente (fase 3)

- **Ninja Gaiden:** separar cada acto en los segmentos `intro`, etapas, `boss` y `outro` (gate G2b). Hoy ya hay un chunk por etapa, pero la escena posterior al jefe queda en el mismo chunk que la pelea. Los segmentos son opcionales: el Act 1 no tiene `intro`.
- **Páginas agregadas** (Bosses, Items y Enemies de Zelda): un chunk por fila, para que G3 bloquee solo la fila de un jefe y no el bloque completo. Hoy se empaquetan varias filas por chunk.
- **Fichas por mazmorra o acto** como documento padre, para la recuperación small-to-big y las pistas escalonadas.
