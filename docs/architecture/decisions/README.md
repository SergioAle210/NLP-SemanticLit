# Decisiones de arquitectura (ADRs)

Cada archivo registra una decisión: contexto, decisión, alternativas y consecuencias. Los ADRs aceptados no se reescriben; si una decisión cambia, se crea uno nuevo que reemplaza al anterior, y el anterior se marca como reemplazado.

| ADR | Decisión | Estado |
| --- | --- | --- |
| [0001](0001-english-first.md) | Primero en inglés; el español es una capa opcional al final | Aceptado |
| [0002](0002-strategywiki-corpus.md) | StrategyWiki como corpus principal, versionado en el repo | Aceptado |
| [0003](0003-access-control-as-spoiler-gates.md) | El control de acceso se modela como gates de spoilers | Aceptado |
| [0004](0004-sqlite-and-demo-profiles.md) | SQLite y perfiles de demo, sin login | Aceptado |
| [0005](0005-wikitext-cleaning.md) | Limpieza de wikitext con mwparserfromhell y reglas explícitas | Aceptado |
| [0006](0006-fixed-chunking-baseline.md) | Chunking fijo por palabras como línea base | Aceptado |
| [0007](0007-per-game-config.md) | Diferencias entre juegos como configuración, no como código | Aceptado |
| [0008](0008-relevance-by-evidence-text.md) | Relevancia definida por evidencia textual, no por chunk_id | Aceptado |
| [0009](0009-phase3-retrieval-config.md) | Recuperación de la fase 3: híbrida e5 + chunking estructural | Aceptado |
| [0010](0010-query-expansion.md) | Transformación de consultas: ortografía + glosario + multi-consulta | Aceptado (a confirmar con preguntas nuevas); fusión modificada por 0011 |
| [0011](0011-flat-fusion-exact-dense.md) | Fusión RRF plana en la multi-consulta y búsqueda semántica exacta | Aceptado |
| [0012](0012-location-aliases-phrase-tokens.md) | Alias de ubicación en el índice y tokens de frase palabra + número | Aceptado |
| [0013](0013-intent-router-and-tools.md) | Router de intención por reglas y herramientas (§5.6) | Aceptado |

Plantilla para nuevos ADRs: `NNNN-titulo-corto.md` con las secciones *Contexto*, *Decisión*, *Alternativas consideradas* y *Consecuencias*.
- [0014](0014-serving-profile-and-secondary-tier.md) Perfil de servicio, segunda búsqueda y alcance de fuentes
