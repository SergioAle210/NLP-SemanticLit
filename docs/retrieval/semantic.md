# Recuperación semántica y búsqueda híbrida

Implementación:
- [embeddings.py](../../src/gamerag/retrieval/embeddings.py): modelos y prefijos;
- [dense.py](../../src/gamerag/retrieval/dense.py): índice en Chroma;
- [hybrid.py](../../src/gamerag/retrieval/hybrid.py): fusión RRF;
- [factory.py](../../src/gamerag/retrieval/factory.py): construcción por nombre, que comparten la evaluación y la API.

Requiere el extra `semantic`: `uv sync --locked --extra semantic --extra ui` si también se utiliza la interfaz. Los comandos posteriores pueden usar `uv run --no-sync` para conservar el entorno sincronizado.

## Modelos de embeddings

Las cifras de tiempo y recuperación de esta sección corresponden al experimento inicial de la fase 3 sobre el corpus y banco indicados; no son mediciones nuevas de la integración actual.

| Clave | Modelo | Idiomas | Dim | Prefijos | Indexar 153 chunks (CPU) | Consulta |
| --- | --- | --- | ---: | --- | ---: | ---: |
| `bge-small-en` | BAAI/bge-small-en-v1.5 | Inglés | 384 | Consulta: `Represent this sentence for searching relevant passages: ` | 11.8 s | ~20 ms |
| `e5-small-multi` | intfloat/multilingual-e5-small | Multilingüe | 384 | `query: ` / `passage: ` | 13.9 s | ~20 ms |

- **Los prefijos son parte del modelo:** cada uno se entrenó con ellos, y omitirlos o usar los de otro modelo degrada la calidad **sin dar error**. Por eso viven en un registro explícito (`MODELS`).
- **Predeterminado:** `e5-small-multi` (`GAMERAG_EMBEDDING_MODEL`), seleccionado en [ADR-0009](../architecture/decisions/0009-phase3-retrieval-config.md). En aquella comparación fue la mejor variante híbrida con chunking estructural (hit rate@5 = 0.89); `bge-small-en` obtuvo mejor MRR (0.72) y sigue disponible. E5 admite consultas multilingües sin cambiar el modelo del índice, pero eso no acredita calidad equivalente en español ([ADR-0001](../architecture/decisions/0001-english-first.md)).
- Los modelos se descargan de Hugging Face a `models/` (aprox. 600 MB los dos; fuera de git). En Windows sin el modo desarrollador aparece un aviso sobre symlinks: es inofensivo, solo implica una caché algo más grande.

## Índice en Chroma

- **Una colección por juego, chunker y modelo**, persistida en `data/index/chroma/` (fuera de git).
- **Qué se indexa:** lo mismo que en BM25, la ruta de la página sin el nombre del juego + los alias de ubicación + el texto del chunk (`index_text` en [bm25.py](../../src/gamerag/retrieval/bm25.py)). Así los dos recuperadores ven la misma información. En el experimento inicial, indexar la ruta subió la semántica con chunking fijo de 0.50 a 0.78 de hit rate@5 ([evaluation/results.md](../evaluation/results.md)).
- **Huella:** la colección incluye contenido, identidad, revisión y metadatos de los chunks, además del modelo y de la versión de representación. Cambios de ubicación, restricciones, URL o revisión invalidan el índice aunque el texto no cambie. La ingesta conserva además su propia huella de configuración y snapshots.
- **Score:** la similitud coseno, calculada como producto punto de vectores normalizados. No depende de cómo cada versión de Chroma reporta la "distancia".
- **Metadatos:** juego, fuente, sección, revisión, página, origen, tipo y ubicación (`quest`, `level`, `act`, `stage`, `restricted`). `DenseIndex.search` admite un **pre-filtro** con `where`, por ejemplo `{"level": 3}`. El pipeline servido recupera candidatos y aplica después los controles de acceso y la proyección de contenido; no transmite ese filtro a la búsqueda híbrida.

## Fusión híbrida: Reciprocal Rank Fusion

```text
rrf(chunk) = Σ por cada ranking  1 / (60 + posición del chunk en ese ranking)
```

- Combina **posiciones**, no puntajes. BM25 (p. ej. 7.12) y la similitud coseno (0 a 1) están en escalas distintas, y sumarlos directamente sería incorrecto (curso, tema 08, diapositiva 198).
- k = 60 es el valor del artículo original de RRF (Cormack, Clarke y Büttcher, 2009). No se ajustó, para no sobreajustarlo a los 18 casos.
- A cada recuperador se le solicitan **hasta 20 candidatos**, sin importar cuántos resultados se pidan a la fusión; BM25 puede devolver menos si no hay suficientes coincidencias positivas. La profundidad solicitada es fija porque RRF con listas más largas cambia el orden de los primeros resultados: en la ablación, con 50 por recuperador el hit rate@5 bajaba de 0.89 a 0.83.
- Un chunk que aparece alto en los dos rankings supera a uno que solo es primero en uno: premia el **acuerdo**.

## Hallazgos

Detalle en [evaluation/results.md](../evaluation/results.md).

- **Dilución:** el embedding de un chunk que mezcla varias secciones es un "promedio" que no se parece a ninguna pregunta concreta. Con chunking estructural, "sail across the sea" pasa de no encontrarse a rank 1.
- **Contexto de la página:** sin la ruta de la página, muchos chunks no dicen dónde ocurren. Indexarla es tan importante como el chunking.
- **BM25 y la búsqueda semántica reaccionan de forma opuesta al tamaño del chunk:** los chunks cortos favorecen a la semántica y perjudican a BM25. La híbrida compensa.
