# Fuentes y gobernanza

Cubre el §5.2 de [course/instructions.md](../course/instructions.md). Decisión: [ADR-0002](../architecture/decisions/0002-strategywiki-corpus.md).

| Fuente | Origen | Licencia / permiso | Formato | Versión | ¿En el repo? |
| --- | --- | --- | --- | --- | --- |
| StrategyWiki: *The Legend of Zelda* (41 páginas) | strategywiki.org, API de MediaWiki | CC BY-SA 4.0 (verificado vía `siteinfo`) | Wikitext | `revid` por página; snapshot del 2026-11-04 | ✅ `data/wiki_snapshot/strategywiki/zelda1/` |
| StrategyWiki: *Ninja Gaiden (NES)* (11 páginas) | Ídem | CC BY-SA 4.0 | Wikitext | Ídem | ✅ `data/wiki_snapshot/strategywiki/ninja_gaiden_nes/` |
| Manual *The Legend of Zelda* | nintendo.co.jp, `CLV-P-NAANE.pdf` | © Nintendo; distribución pública gratuita; uso educativo sin lucro, sin redistribuir | PDF | NES Classic | ❌ **Descartado** (2026-11-06): la wiki cubre el contenido |
| Manual *Ninja Gaiden* | nintendo.co.jp, `CLV-P-NACBE.pdf` | Ídem | PDF | NES Classic | ❌ **Descartado** |
| Datos curados (hechos, fichas, prerrequisitos, entidades) | El equipo, a partir de la wiki | Derivado, por lo tanto CC BY-SA 4.0 | JSON / YAML | `v1` | No se creó: la tabla de jefes se extrae de la wiki al cargar ([tools/](../tools/README.md)) |

## Política

- La wiki y sus derivados se versionan **con atribución** ([data/wiki_snapshot/README.md](../../data/wiki_snapshot/README.md)).
- **No se versionan:** manuales, texto OCR, imágenes, logos (`data/raw/` está en `.gitignore`).
- **Tampoco se versionan los artefactos regenerables** (`data/processed/`, `data/index/`, `state/*.sqlite3`).
- No se usan copias de manuales de sitios de terceros (gamesdatabase.org, s.mprd.se).
- Información sensible: el corpus no contiene datos personales. Los logs de auditoría sanitizan PII y nunca registran la API key ([security/controls.md](../security/controls.md)).

## Snapshot

- **Descarga:** [scripts/download_wiki.py](../../scripts/download_wiki.py) (API de MediaWiki, pausa de 0.5 s entre requests, reintentos ante fallas de red).
- **Archivos:** cada página se guarda en `pages/*.wiki` con saltos de línea LF; `manifest.json` registra título, URL, `revid` y tamaño.
- **Saltos de línea:** `.gitattributes` fuerza LF para que el `hash` de cada chunk sea idéntico en Windows, macOS y Docker.
- **Reproducibilidad:** volver a descargar puede traer revisiones nuevas. El snapshot versionado es la referencia de la evaluación.
