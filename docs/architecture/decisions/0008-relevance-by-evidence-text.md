# ADR-0008: Relevancia definida por evidencia textual, no por chunk_id

**Estado:** aceptado (2026-11-05)

## Contexto

Para calcular Recall@k y MRR hay que saber qué chunks son relevantes para cada caso. El ejemplo del curso usa `relevant_chunk_id`, pero los `chunk_id` cambian con la estrategia de chunking (fijo contra estructural), y el proyecto debe comparar justamente esas estrategias.

## Decisión

Cada caso declara su **evidencia**: fragmentos de texto literales del corpus, organizados en partes y alternativas.

```json
"evidence": [["Blue Candle 60 R", "Blue Candle for 60 rupees"], ["burn bushes in the overworld"]]
```

- **Un chunk es relevante** si proviene de una de las `expected_sources` y contiene alguna alternativa de alguna parte (comparación sin mayúsculas y con espacios normalizados).
- **Una pregunta compuesta** tiene varias partes. **Coverage@k** mide qué fracción de las partes aparece en el top-k.
- `expected_sources` y `expected_pages` (campos obligatorios del curso) se derivan de dónde aparece la evidencia en el corpus limpio.

## Alternativas consideradas

- **`relevant_chunk_id` fijo.** Hay que reetiquetar el banco cada vez que cambia el chunking, y la comparación entre estrategias deja de ser justa.
- **Juicio manual de cada candidato.** Es costoso y no es reproducible en cada corrida.
- **Similitud semántica con una respuesta de referencia.** Introduce un modelo en la definición de relevancia.

## Consecuencias

- El mismo banco evalúa cualquier chunking y cualquier recuperador.
- Los tests garantizan la integridad del banco: cada caso con respuesta tiene al menos un chunk relevante, y cada par (fuente, sección) esperado contiene la evidencia.
- La evidencia debe ser corta (unas pocas palabras), para que no quede partida entre dos chunks.
- Un chunk que trata el tema pero no contiene la frase de evidencia no cuenta como relevante. La medida es conservadora: puede subestimar el recall, nunca sobreestimarlo.
