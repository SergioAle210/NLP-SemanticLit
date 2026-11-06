# ADR-0013: Router de intención por reglas y herramientas (§5.6)

**Estado:** aceptado (2026-11-06).

## Contexto

- **El §5.6 exige** al menos una herramienta o flujo agéntico "realmente necesario".
- **Hay dos tipos de pregunta que el RAG no resuelve bien:**
  - **listas o tablas:** "list all the bosses in the first quest" sale parcial, porque la lista está repartida en varios chunks ([evaluation/results.md](../../evaluation/results.md));
  - **preguntas sobre el propio jugador:** "what should I do next?" depende del perfil, no de la wiki.
- **Las acciones** ("I just beat level 3") no deben responderse con texto ni ejecutarse sin confirmación.

## Decisión

- **Flujo de decisión** (opción 2 del §5.6) con un **router por reglas** entre los guards de entrada y la recuperación. Elige entre:
  - `documents`;
  - `query_game_facts`: SQL de solo lectura sobre la tabla de jefes extraída de la wiki;
  - `next_available_levels`: perfil;
  - `update_progress`: no se ejecuta, `needs_human_review`.
- **Las filas de las herramientas pasan por los mismos `AccessFilter`** que los chunks.
- **Ante una falla, se degrada al RAG.**
- **Se activa con `GAMERAG_ROUTER`** (por defecto, `true`).

Detalle en [tools/README.md](../../tools/README.md).

## Alternativas consideradas

- **Router con LLM (Haiku con tool use).** Generaliza mejor, pero cuesta tokens y latencia en cada pregunta, no es determinista y requiere la API key. Las reglas son auditables y suficientes para tres intenciones bien delimitadas. Queda como comparación cuando esté Haiku.
- **Agente autónomo (opción 3).** El problema no requiere planificar varios pasos; agregaría riesgo sin necesidad funcional, algo que el §5.6 desaconseja.
- **Ejecutar `update_progress` directamente.** Cambiar el progreso cambia qué contenido ve el jugador (los gates de spoilers): es una acción crítica (§10) y requiere confirmación humana.
- **SQL libre generado por un LLM** (text-to-SQL). Superficie de inyección innecesaria; las consultas predefinidas cubren las preguntas.

## Consecuencias

- **El router es conservador:** ante la duda, va a `documents`. Ninguna de las 39 preguntas del banco cambia de ruta, así que **la evaluación de recuperación no cambia**. Lo verifica un test.
- **Las reglas son en inglés y cubren formulaciones previstas;** una formulación no prevista cae al RAG, que es el comportamiento anterior.
- **Ninja Gaiden** no tiene tabla de jefes ni `next_available_levels` (es lineal), así que solo usa `update_progress` y `documents`.
- **La tabla se extrae de una sola página** (Bosses); agregar otras (tiendas, ítems) sigue el mismo patrón.
