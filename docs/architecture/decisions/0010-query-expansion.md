# ADR-0010: Transformación de consultas con glosario y multi-consulta (sin LLM)

**Estado:** aceptado (2026-11-06). Debe confirmarse con preguntas nuevas del equipo.

## Contexto

- Las preguntas escritas por el equipo como jugadores reales ("how do i atack?", "how can i heal?", "what is the best weapon?") rendían mucho peor que las del banco original: Recall@5 de **0.50** contra 0.89.
- El diagnóstico mostró un **desajuste de vocabulario** (attack ↔ swing the sword, money ↔ rupees) y errores de tipeo.
- Se probaron y **rechazaron** el reranker cross-encoder y el chunking por fila.

## Decisión

- Recuperación **multi-consulta**: la pregunta original + una variante con **corrección ortográfica conservadora** + **términos de un glosario por juego**. Se fusionan con RRF y la original se conserva en la traza (`query_variants`).
- Activada por defecto (`GAMERAG_QUERY_EXPANSION=true`), sobre la configuración del [ADR-0009](0009-phase3-retrieval-config.md).
- **Se descartan las reglas de identificadores** (Level → Dungeon, first quest → quest 1): en la ablación bajaron las preguntas del curso de 0.89 a 0.78.

## Alternativas consideradas

- **Reescritura con Haiku.** Es la estrategia típica del curso y generaliza mejor, pero requiere la API key (aún no disponible), cuesta tokens y latencia, y puede cambiar la intención. Queda como comparación futura.
- **Reranker cross-encoder.** Rechazado: Recall@5 de 0.89 a 0.78, unas 40 veces más lento.
- **Chunking por fila.** Rechazado: Recall@5 de 0.89 a 0.78.
- **Reemplazar la pregunta por la variante.** Si la variante es mala, se pierde la intención original; la multi-consulta conserva ambas.

## Consecuencias

- Equipo: 0.50 → **0.75**. Robustez: 0.56 → 0.83. Total: 0.72 → **0.86**. **Sin pérdida en las preguntas del curso** (0.89). Latencia de 20 ms a 29 ms.
- **Riesgo de sobreajuste reconocido:** el glosario se escribió conociendo los fallos. Para validarlo hace falta una segunda tanda de preguntas del equipo, con el glosario congelado. Si la mejora no se sostiene, se reporta así.
- El glosario es manual y por juego (configuración, [ADR-0007](0007-per-game-config.md)). Ninja Gaiden aún no tiene glosario.
- **No resuelve la abstención.** Los puntajes de recuperación no separan las preguntas con respuesta de las que no la tienen ([evaluation/results.md](../../evaluation/results.md)); la abstención queda a cargo del generador.
