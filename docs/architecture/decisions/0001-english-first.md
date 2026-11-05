# ADR-0001: Primero en inglés

**Estado:** aceptado (2026-11-05)

## Contexto

- El corpus (StrategyWiki) y los manuales están solo en inglés.
- El curso no exige un idioma. La presentación pone como ejemplo de algo fuera del alcance el "soporte multiidioma no validado", es decir, cualquier idioma que se ofrezca debe estar evaluado.
- La prioridad es tener al menos una línea base que funcione bien.

## Decisión

Todo el sistema funciona y se evalúa **primero en inglés**: preguntas, corpus, respuestas y banco de pruebas. El español es una capa opcional al final (fase 3d), sobre un sistema ya evaluado.

## Alternativas consideradas

- **Español desde el inicio, con traducción de la consulta.** Mezcla dos fuentes de error (recuperación y traducción) en la línea base, y BM25 no funciona entre idiomas sin traducir.
- **Traducir el corpus al español.** Las citas dejarían de apuntar al texto original, se introducen errores de traducción, y los nombres oficiales en español no coinciden con una traducción literal.

## Consecuencias

- BM25 rinde al máximo, porque las palabras coinciden literalmente.
- Si la línea base falla, la causa está en la limpieza, el chunking o la recuperación, no en una traducción.
- **Modelos (se decide en la fase 3a):** se comparan embeddings en inglés y multilingües sobre el banco en inglés. Si la diferencia de Recall@5 es de 0.02 o menos, se queda el multilingüe, para que la fase 3d no requiera reindexar.
- **Diseño previsto para la fase 3d:**
  - la pregunta original va a la búsqueda semántica (multilingüe) y la traducida al inglés va a BM25;
  - un glosario de términos por juego (escalera → Ladder) guía la traducción;
  - la respuesta sale en el idioma de la pregunta;
  - se valida con casos en español y una ablación de idioma.

  Se apoya en evidencia de que BM25 rinde mal entre idiomas, que los embeddings multilingües manejan bien el par español-inglés ([arXiv 2511.19324](https://arxiv.org/pdf/2511.19324)), y que traducir la consulta puede introducir errores ([arXiv 2504.03616](https://arxiv.org/html/2504.03616v2)).
