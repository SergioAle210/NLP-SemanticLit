# ADR-0005: Limpieza de wikitext con mwparserfromhell y reglas explícitas

**Estado:** aceptado (2026-11-05)

## Contexto

El wikitext de StrategyWiki usa unas 40 plantillas distintas, algunas anidadas (`{{ContentBox|title={{a|White Sword}}|contents=...}}`), además de tablas con atributos y listas dentro de las celdas. El inventario completo y las reglas están en [ingestion/cleaning.md](../../ingestion/cleaning.md).

## Decisión

- Parsear con **mwparserfromhell** (MIT), el parser de wikitext estándar en Python, y procesar las plantillas de adentro hacia afuera.
- Cada plantilla tiene una **regla explícita**: descartar, reemplazar por un argumento o convertir en subsección.
- Las plantillas **sin regla se descartan y se cuentan** en las estadísticas de la ingesta, y un test exige que el conteo sea cero sobre todo el corpus.
- Las tablas se aplanan a una línea por fila con pares `Encabezado: valor`.

## Alternativas consideradas

- **Solo expresiones regulares.** Fallan con plantillas anidadas y con `|` dentro de enlaces.
- **`strip_code()` de mwparserfromhell.** Elimina todas las plantillas, incluidas las que contienen contenido ({{im/loz|Item|Raft}} → "Raft"), y mezcla las celdas de las tablas.
- **Pedir el HTML renderizado a la API.** Agrega una dependencia de red en cada ingesta y obliga a limpiar HTML en lugar de wikitext.

## Consecuencias

- Una plantilla nueva (p. ej. al agregar un juego) no se pierde en silencio: rompe un test y hay que escribir su regla.
- Las filas de las tablas quedan legibles y autocontenidas ("Name: Octorok | HP: 1 / 2 | Damage: 1 | Description: ..."), lo que favorece tanto a BM25 como al LLM.
- Agrega una dependencia liviana de Python puro.
