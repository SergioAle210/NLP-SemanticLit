# ADR-0002: StrategyWiki como corpus principal, versionado en el repo

**Estado:** aceptado (2026-11-04)

## Contexto

- Los manuales oficiales son cortos (20 a 40 páginas con muchas ilustraciones), casi no tienen contenido organizado por etapas y son © Nintendo, por lo que no se pueden redistribuir.
- El control de spoilers necesita contenido organizado por ubicación en el juego.

## Decisión

- **StrategyWiki** es el corpus principal: licencia CC BY-SA 4.0, verificada vía la API (`siteinfo`).
- Se descarga con la API de MediaWiki ([scripts/download_wiki.py](../../../scripts/download_wiki.py)) y se **versiona en el repo** como snapshot congelado, con el `revid` de cada página.
- Los manuales oficiales son una fuente secundaria (controles, objetos, premisa). Se descargan solo localmente y no se versionan.

## Alternativas consideradas

- **Zelda Wiki o Fandom.** Usan licencia GFDL, que es más engorrosa de cumplir. Además, StrategyWiki tiene una página por mazmorra y por quest, lo que hace casi automático el etiquetado de ubicación.
- **Solo los manuales.** Corpus insuficiente para el banco de pruebas y para el control de spoilers.
- **Descargar en cada build.** La wiki cambia, y la evaluación dejaría de ser reproducible.

## Consecuencias

- El snapshot es la referencia reproducible. El `revid` sirve como "versión documental" (§5.2 y §8).
- Todo derivado del snapshot (texto limpio, chunks, fichas) se publica también bajo CC BY-SA 4.0 ([data/sources.md](../../data/sources.md)).
- El texto de la wiki usa coordenadas de mapas ("B-3, section six") que no se entienden sin imagen. Por eso la navegación cuarto por cuarto queda fuera del alcance.
