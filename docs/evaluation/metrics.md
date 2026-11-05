# Métricas y comparación

Cubre el §9 de [course/instructions.md](../course/instructions.md). Script previsto: `eval/run_benchmark.py`, que llama a la misma API que la interfaz y guarda los resultados en `eval/results/<fecha>_<variante>.json`. Las métricas se reportan **por juego y en total**.

| Dimensión | Métricas | Meta ([problem-and-scope.md](../overview/problem-and-scope.md)) |
| --- | --- | --- |
| Recuperación | Recall@k (k = 1, 3, 5), MRR, Precision@k, redundancia del top-k | Recall@5 ≥ 0.80 |
| Respuesta | Precisión de citas, abstención correcta, fidelidad, cobertura | Citas ≥ 0.90, abstención ≥ 90% |
| Operación | Latencia media y P95, tokens, llamadas al LLM, costo por consulta | P95 < 6 s |
| Seguridad | % de ataques bloqueados, spoilers filtrados, contaminación entre juegos, acciones sin confirmar | 0 spoilers, 0 contaminación, 0 acciones sin confirmar |

**Fidelidad y cobertura** se miden con un LLM como juez, validado contra una muestra revisada a mano.

## Variantes a comparar

- **Línea base contra versión mejorada** ([architecture/overview.md](../architecture/overview.md)).
- **Ablaciones:**
  - chunking fijo contra estructural;
  - solo BM25, solo vectorial e híbrida;
  - con y sin reranker;
  - embeddings en inglés contra multilingües;
  - sin G1, sin G2b, sin G3 y sin filtro de quest.
- **Fase 3d:** ablaciones de idioma ([ADR-0001](../architecture/decisions/0001-english-first.md)).

## Datos de la ingesta para el informe

Las estadísticas de `data/processed/<juego>/stats.*.json` documentan cada variante de chunking. El dato de la línea base es que el 61% de los chunks de Zelda cruzan más de una sección ([ingestion/chunking.md](../ingestion/chunking.md)).

## Análisis de fallas

Al menos 3 fallas reales, diagnosticadas con la traza de auditoría (pregunta → intención → filtros → candidatos → scores → contexto → respuesta).
