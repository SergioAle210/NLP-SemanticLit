# Métricas y comparación

Cubre el §9 de [course/instructions.md](../course/instructions.md). Las métricas se reportan **por juego, por categoría y en total**. La recuperación y la generación se evalúan **por separado**: se puede recuperar bien y generar mal, y viceversa.

| Evaluación | Comando | Estado |
| --- | --- | --- |
| Recuperación (sin LLM) | `uv run python -m gamerag.evaluation.retrieval <juego>` | ✅ ([results.md](results.md)) |
| Sistema completo (vía API) | Pendiente | ⬜ |

Cada corrida se guarda en `eval/results/<fecha>_<juego>_<variante>.json`, **con los candidatos de cada caso** (rank, score, chunk y si es relevante), para poder diagnosticar fallas.

## Definiciones de recuperación

Según el curso (tema 08), implementadas en [metrics.py](../../src/gamerag/evaluation/metrics.py) y verificadas con los ejemplos de las diapositivas:

| Métrica | Definición |
| --- | --- |
| Recall@k | Consultas con al menos un chunk relevante en el top-k / total de consultas |
| Precision@k | Chunks relevantes en el top-k / k |
| MRR | Promedio de 1 / posición del primer relevante (0 si no aparece) |
| Coverage@k (propia) | Fracción de las partes de evidencia cubiertas en el top-k (para preguntas compuestas) |

Los casos sin respuesta no entran en estas métricas; se evalúan con la abstención en la generación.

## Todas las dimensiones

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
