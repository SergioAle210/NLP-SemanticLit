# Pipeline de consulta

Implementación: [src/gamerag/pipeline.py](../../src/gamerag/pipeline.py). Es el punto único que usarán la API y la evaluación del sistema completo.

```python
pipe = build_pipeline(get_settings())        # híbrida e5 + estructural, extractivo, guards por defecto
answer, trace = pipe.ask("How can I sail across the sea?", "zelda1", profiles["novato"])
context, trace = pipe.search("How can I sail across the sea?", "zelda1", profiles["novato"])  # etapas 1-3, sin generar
```

`search` ejecuta solo los guards de entrada, la recuperación y los filtros, y devuelve el contexto que recibiría el generador sin generar (útil para depurar sin gastar tokens; `trace.outcome = "retrieved"`). Lo expone la API en `POST /search` ([api/](../api/README.md)).

## Etapas

| # | Etapa | Si falla o bloquea | `trace.outcome` |
| ---: | --- | --- | --- |
| 1 | `InputGuard`s | Abstención sin buscar | `rejected_input` |
| 1b | **Router** ([tools/](../tools/README.md)): `documents` o una herramienta. Las filas de la herramienta pasan por los `AccessFilter` y la respuesta, por los `OutputGuard`s | Parámetros inválidos: abstención con `tool_used`. Si la herramienta falla, sigue por el RAG | `answered` o `abstained` |
| 2 | Recuperación: `candidates` (50) del recuperador del juego | — | — |
| 3 | `AccessFilter`s sobre cada candidato → los primeros `top_k` (5) permitidos | Si todo lo bloquea un gate de spoilers: `blocked_by_spoiler` | `blocked_by_access` |
| 4 | `Generator` | (El `FallbackGenerator` degrada al extractivo) | — |
| 5 | `OutputGuard`s | Abstención con `needs_human_review` | `rejected_output` |
| — | Fin | — | `answered` o `abstained` |

**¿Por qué 50 candidatos y no 5?** Los filtros pueden descartar varios. Si se recuperaran solo 5 y se bloquearan 3, al generador le llegarían 2 aunque hubiera más evidencia permitida.

## Traza (`Trace`)

Es la cadena auditable de la diapositiva 16 del curso: pregunta → filtros → candidatos → scores → contexto → generador → respuesta.

| Campo | Contenido |
| --- | --- |
| `trace_id` | Identificador; también va en `Answer.trace_id` |
| `question`, `game`, `user_id`, `role` | Quién preguntó qué |
| `retriever`, `generator` | Configuración usada (p. ej. `hybrid+qx/structural`, `extractive`) |
| `query_variants` | Formulaciones usadas en la búsqueda: `[0]` es la pregunta original y `[1]`, la corregida y expandida ([retrieval/query-expansion.md](../retrieval/query-expansion.md)). En el log de auditoría se redactan igual que la pregunta |
| `input_guards`, `output_guards` | `{nombre: "ok" o motivo}` |
| `candidates` | Rank, `chunk_id`, score y `blocked_by` de cada candidato |
| `context` | `chunk_id`s entregados al generador (o citados por la herramienta) |
| `route`, `route_reason`, `tool` | Decisión del router y, si hubo herramienta: `name`, `params`, `status` (`ok`, `invalid_params` o `degraded`), filas y filas bloqueadas |
| `outcome` | Resultado final (tabla de arriba) |
| `latency_ms` | Por etapa: `input`, `router` o `tool`, `retrieval`, `access`, `generation`, `output` |

La traza se guardará en SQLite como log de auditoría, con la PII sanitizada ([ADR-0004](../architecture/decisions/0004-sqlite-and-demo-profiles.md)).

## Configuración

`settings.py` / `.env`:

| Variable | Valor por defecto |
| --- | --- |
| `GAMERAG_RETRIEVER` | `hybrid` |
| `GAMERAG_CHUNKER` | `structural` |
| `GAMERAG_EMBEDDING_MODEL` | `e5-small-multi` |
| `GAMERAG_QUERY_EXPANSION` | `true` |
| `GAMERAG_TOP_K` | `5` |
| `GAMERAG_CANDIDATES` | `50` |

Requisitos: haber corrido la ingesta con el chunker configurado y, para `dense` o `hybrid`, el extra `semantic`.

## Bugs detectados al integrar

**Lo servido debe ser lo medido.** La híbrida fusionaba rankings de profundidad `max(k, 20)`; como el pipeline pide 50 candidatos, servía Recall@5 = 0.83 en lugar del 0.89 evaluado. Ahora la profundidad de la fusión es fija (20), y un test verifica que el pipeline servido alcance el Recall@5 evaluado ([evaluation/results.md](../evaluation/results.md), "Verificación").

**Chunks con score 0.** La primera prueba de punta a punta mostró que **BM25 devolvía chunks con score 0**, rellenando el top-k en el orden del corpus, y que **RRF los premiaba por aparecer en la lista**. Con 50 candidatos, a "How can I sail across the sea?" le respondía primero la página de controles. Se corrigió: BM25 solo devuelve chunks con score > 0, y hay un test de regresión. Con 20 candidatos (la profundidad de la evaluación), el efecto en las métricas fue mínimo ([evaluation/results.md](../evaluation/results.md)).
