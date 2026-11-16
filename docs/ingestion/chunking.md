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
| Unidad | Palabras | Segmentación independiente del tokenizador del generador |
| Límite | La página | La página es la unidad de cita; un chunk nunca mezcla fuentes |
| Secciones | Se ignoran | A propósito: es la línea base del chunking estructural |

**Detalles:**

- El título de cada sección se antepone como `[Ruta > De > Sección]`. Le da contexto al lector y términos a BM25.
- Los saltos de línea se conservan, para que las filas de tablas y las listas sigan siendo legibles. Solo las palabras cuentan para el tamaño.
- Cada chunk registra la sección donde empieza (`section`, `page`) y todas las que abarca (`sections`).

## Limitaciones medidas en el experimento inicial

Las cantidades y métricas de esta sección corresponden al corpus primario inicial. Se conservan como antecedentes de la selección estructural, no como estadísticas nuevas de los siete juegos.

- **El 61% de los chunks de Zelda (94 de 153) y el 46% de los de Ninja Gaiden (32 de 70) cruzan más de una sección.** Un chunk puede mezclar, por ejemplo, el final del recorrido de una mazmorra con su jefe.
- Muchos chunks empiezan a mitad de una frase, por el paso fijo de la ventana.
- Un chunk que cruza secciones puede mezclar etapas o una pelea con la escena posterior. En el servicio actual, los controles de acceso se aplican también a la línea base; la política de contenido excluye de forma conservadora ventanas que cortan material sensible.

## Chunking estructural (`structural-w225-m15`, fase 3)

Es la configuración elegida para la fase 3 ([ADR-0009](../architecture/decisions/0009-phase3-retrieval-config.md)). Se generó con `--chunker structural`.

| Regla | Valor | Motivo |
| --- | --- | --- |
| Unidad | **Una sección** (o parte de una) | Cada chunk trata un solo tema: evita la dilución del embedding |
| Secciones largas | Se dividen **empaquetando líneas completas** (filas de tabla, ítems, párrafos) hasta 225 palabras de cuerpo; el encabezado se repite en cada parte | Se preservan las líneas que caben; si una supera el máximo, se divide por palabras. La cifra de 185 palabras correspondía al corpus inicial |
| Secciones diminutas | Menos de **15 palabras** → se unen a la siguiente de la página, si el total cabe en 225 | Evita chunks sin contexto como "[Prerequisites] Raft." El umbral es bajo a propósito: unir secciones de temas distintos reintroduce la dilución. Por ejemplo, la sección del Raft (24 palabras) queda sola |
| Solapamiento | Ninguno | Se prefieren límites de línea y el encabezado aporta contexto; una línea demasiado larga sí puede quedar partida |
| Encabezado | `[Ruta > De > Sección]` por cada sección incluida | Contexto para el lector y términos para la búsqueda |

**Resultado medido:**

| | Fijo | Estructural |
| --- | ---: | ---: |
| Chunks (Zelda / NG) | 153 / 70 | 243 / 84 |
| Palabras por chunk, media (Zelda) | 201 | 110 |
| Chunks que mezclan secciones (Zelda / NG) | **61% / 46%** | **9% / 0%** |

El 9% restante son las secciones diminutas unidas a la siguiente (p. ej. "Enemy drops > Heart" con "Enemy drops > Rupees").

**Efecto histórico en la recuperación** ([evaluation/results.md](../evaluation/results.md)):

- **Mejora la búsqueda semántica:** "sail across the sea" pasa a rank 1; MRR de bge de 0.61 a 0.72.
- **Empeora BM25:** Recall@5 de 0.78 a 0.61.
- La híbrida e5 alcanza **Recall@5 = 0.89**.

## Política de contenido y trabajo futuro

- **Ninja Gaiden:** `ContentPolicy` separa tácticas y desenlaces mediante reglas curadas; exige etapa posterior para el contenido narrativo. No se presenta como un segmentador semántico universal.
- **Páginas agregadas:** la política proyecta pasajes y filas autorizadas conservando identidad y revisión. La segmentación global por fila se probó y descartó históricamente (Recall@5 0.89 → 0.78); esa comparación se conserva y no equivale a la proyección selectiva actual.
- **Mapas Hyrule 1–8:** la proyección exige acceso a los niveles mencionados en cada celda y a sus dependencias indirectas configuradas. Conserva las celdas útiles autorizadas y descarta prefijos o colas sin límites comprobables, también con `fixed`, `structural` o `rows` de tamaño reducido. Los cinco corazones de White Sword no se interpretan como una referencia al nivel 5.
- **Fichas por mazmorra o acto** (small-to-big y pistas escalonadas): no se implementaron; quedan como trabajo futuro.
