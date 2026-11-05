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

## Fase 3: chunking estructural (pendiente)

- **Un chunk por sección.** Si la sección pasa de aprox. 300 tokens, se divide con 15% de solapamiento; si es muy corta, se une con la siguiente de la misma página.
- **Páginas agregadas** (Bosses, Items y Enemies de Zelda): un chunk por fila de tabla o por ContentBox.
- **Ninja Gaiden:** cada acto se separa en los segmentos `intro`, etapas, `boss` y `outro`. Los segmentos son opcionales: el Act 1 no tiene `intro`.
- **Fichas por mazmorra o acto** como documento padre, para la recuperación small-to-big y las pistas escalonadas.
- **Comparación contra la línea base** en el banco de pruebas ([evaluation/](../evaluation/)).
