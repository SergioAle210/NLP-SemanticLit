# ADR-0006: Chunking fijo por palabras como línea base

**Estado:** aceptado (2026-11-05)

## Contexto

El curso pide una estrategia de chunking justificada (§5.3) y comparar una línea base contra una versión mejorada (§9). El detalle está en [ingestion/chunking.md](../../ingestion/chunking.md).

## Decisión

- **Línea base:** ventana deslizante de **225 palabras con 30 de solapamiento** (aprox. 300 tokens y 13%), **dentro de cada página**, ignorando a propósito los límites de sección.
- **Unidad de medida:** palabras, no tokens, para no depender de un tokenizador. En inglés, 1 palabra equivale a aprox. 1.3 tokens.
- **Versión mejorada (fase 3):** chunking estructural por sección, más fichas como documento padre.

## Alternativas consideradas

- **Empezar directamente con chunking estructural.** Sin una línea base simple, no hay contra qué medir la mejora.
- **Chunks por tokens con el tokenizador del modelo de embeddings.** Ata la línea base a un modelo que todavía no está decidido ([ADR-0001](0001-english-first.md)).
- **Permitir que un chunk cruce páginas.** Rompe la cita: la página es la unidad de fuente.

## Consecuencias

- Resultado medido con la configuración por defecto: 153 chunks en Zelda y 70 en Ninja Gaiden. **El 61% de los chunks de Zelda (94 de 153) cruzan más de una sección**, y muchos empiezan a mitad de una frase. Es la debilidad que el chunking estructural debe corregir, y es medible.
- Un chunk que cruza secciones hereda la ubicación de la sección donde empieza. Es aceptable en la línea base, que no tiene gates, pero no en la fase 3.
- Los parámetros quedan registrados en cada chunk (`chunker: fixed-w225-o30`), así que los resultados son comparables entre ingestas.
