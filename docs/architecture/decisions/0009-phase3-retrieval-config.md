# ADR-0009: Configuración de recuperación de la fase 3: híbrida e5 + chunking estructural

**Estado:** aceptado (2026-11-05)

## Contexto

Se compararon 10 configuraciones de recuperación sobre los 18 casos con respuesta de Zelda: tres recuperadores (BM25, semántica y híbrida RRF), dos modelos de embeddings (bge-small-en, multilingual-e5-small) y dos chunkings (fijo y estructural). Los resultados y el diagnóstico están en [evaluation/results.md](../../evaluation/results.md).

## Decisión

- **Configuración de la fase 3:** búsqueda **híbrida** (BM25 + `e5-small-multi`, fusión RRF con k = 60) sobre **chunking estructural** (`structural-w225-m15`).
- **Métrica que decide:** **Recall@5**. El LLM recibe 5 chunks, y lo determinante es si la evidencia está entre ellos. Esta configuración obtiene el mejor Recall@5: 0.89, contra 0.78 de la línea base.
- **Lo que se indexa** es lo mismo en los dos recuperadores: la ruta de la página sin el nombre del juego + el texto del chunk.
- **La línea base** (BM25 + chunking fijo) se conserva como referencia de comparación ([ADR-0006](0006-fixed-chunking-baseline.md)).

## Alternativas consideradas

- **Semántica bge estructural.** Tiene el mejor orden (MRR 0.72, Recall@1 0.61), pero menor Recall@5 (0.78). Sería preferible si el LLM recibiera 1 o 2 chunks, o tras un reranker.
- **Híbrida bge estructural.** Recall@5 0.83, un caso menos que e5. Es solo inglés, así que la fase 3d obligaría a reindexar ([ADR-0001](0001-english-first.md)).
- **BM25 estructural.** Recall@5 0.61: el chunking estructural perjudica a BM25.
- **Ajustar `b` de BM25 o el k de RRF.** Se descartó por ahora: hacerlo sobre los mismos 18 casos sería sobreajustar. Se puede revisar si el banco crece.

## Consecuencias

- Se confirma `e5-small-multi` como modelo por defecto, que además deja abierta la fase 3d sin reindexar.
- **El orden (MRR 0.55) es el punto débil** de esta configuración. Un reranker sobre los candidatos de la híbrida es la mejora candidata para la fase 3a; se medirá contra esta configuración.
- Las diferencias entre variantes cercanas son de **un caso** (0.056). La decisión se apoya en las tendencias, que son consistentes (el chunking estructural ayuda a la búsqueda semántica; la híbrida maximiza el recall), y debe revisarse cuando el banco crezca.
