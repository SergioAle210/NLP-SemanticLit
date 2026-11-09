# Snapshots de wiki (corpus del RAG)

Contenido descargado de **[StrategyWiki](https://strategywiki.org)** mediante la API de MediaWiki con [`scripts/download_wiki.py`](../../scripts/download_wiki.py).

## Licencia y atribución

- El contenido de StrategyWiki está publicado bajo **[Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/)**. Verificado vía `api.php?action=query&meta=siteinfo&siprop=rightsinfo` el 2026-11-04.
- **Atribución:** "The Legend of Zelda" y "Ninja Gaiden (NES)", colaboradores de StrategyWiki. La URL y el `revid` de cada página están en `manifest.json`, y el historial de autores puede consultarse en cada URL.
- **Share-alike:** cualquier derivado de estos archivos (texto limpio, chunks, resúmenes) que se distribuya debe mantenerse bajo CC BY-SA 4.0.
- Se descargó **solo texto (wikitext)**. No se incluyen imágenes: las referencias `[[File:...]]` del wikitext se eliminan en la limpieza.
- Esta licencia aplica **solo a esta carpeta**. El manual oficial de Nintendo es © Nintendo y **no** se incluye en el repositorio.

## Contenido

| Carpeta | Juego | Páginas | Caracteres (wikitext) | Fecha |
| --- | --- | ---: | ---: | --- |
| `strategywiki/zelda1/` | The Legend of Zelda (NES, 1986) | 41 | 194,218 | 2026-11-04 |
| `strategywiki/ninja_gaiden_nes/` | Ninja Gaiden (NES, 1988) | 11 | 74,582 | 2026-11-04 |

Cada carpeta contiene:

- `pages/*.wiki`: el wikitext crudo de cada página. Los nombres de archivo usan `__` en lugar de `/`.
- `manifest.json`: título, URL, `revid` (versión exacta de la página), archivo y tamaño de cada página.

## Reproducir

```bash
python scripts/download_wiki.py "The Legend of Zelda" data/wiki_snapshot/strategywiki/zelda1
```

> Ojo: volver a descargar puede traer revisiones más nuevas. Para que la evaluación sea reproducible, el snapshot versionado en git es la referencia, y el `revid` del manifiesto identifica la versión documental.


## Corpus multi-fuente (2026-11-08)

Cada juego combina varias wikis (`config/sources.yaml`, descargadas con `scripts/fetch_corpus.py`). La licencia es la
que reporta la API de cada sitio; **las wikis de Zelda (zeldapedia, zeldawiki) usan GFDL**, un copyleft distinto de
CC BY-SA: se mantienen en carpetas separadas, con atribución por página (`manifest.json` guarda URL y `revid`) y no deben
redistribuirse mezcladas con el resto sin revisar la licencia. Fandom reporta "CC-BY-SA" sin versión (normalmente 3.0).
Los chunks de las fuentes extra quedan **restringidos** (`location.restricted`) hasta que se les asigne una ubicación.

| Juego | Fuente | Licencia | Páginas | KB wikitext |
| --- | --- | --- | ---: | ---: |
| `ac2` | ac_fandom | CC BY-SA | 8 | 92 |
| `doom` | doom_fandom | CC BY-SA | 41 | 211 |
| `gta_sa` | grandtheftwiki | CC BY-SA 3.0 | 215 | 1226 |
| `gta_sa` | gta_fandom | CC BY-SA | 106 | 1234 |
| `ninja_gaiden_nes` | ninjagaiden_fandom | CC BY-SA | 34 | 177 |
| `rdr1` | reddead_fandom | CC BY-SA | 54 | 626 |
| `ac2` | strategywiki | CC BY-SA 4.0 | 31 | 227 |
| `doom` | strategywiki | CC BY-SA 4.0 | 39 | 167 |
| `gta_sa` | strategywiki | CC BY-SA 4.0 | 172 | 788 |
| `ninja_gaiden_nes` | strategywiki | Creative Commons Attribution-ShareAlike 4.0 | 11 | 75 |
| `oot` | strategywiki | CC BY-SA 4.0 | 45 | 774 |
| `rdr1` | strategywiki | CC BY-SA 4.0 | 11 | 40 |
| `zelda1` | strategywiki | Creative Commons Attribution-ShareAlike 4.0 | 41 | 194 |
| `ac2` | wikipedia | CC BY-SA 4.0 | 1 | 78 |
| `doom` | wikipedia | CC BY-SA 4.0 | 1 | 131 |
| `gta_sa` | wikipedia | CC BY-SA 4.0 | 1 | 176 |
| `ninja_gaiden_nes` | wikipedia | CC BY-SA 4.0 | 2 | 74 |
| `oot` | wikipedia | CC BY-SA 4.0 | 1 | 134 |
| `rdr1` | wikipedia | CC BY-SA 4.0 | 1 | 169 |
| `zelda1` | wikipedia | CC BY-SA 4.0 | 1 | 78 |
| `oot` | zeldapedia | GFDL | 59 | 1258 |
| `zelda1` | zeldapedia | GFDL | 54 | 1407 |
| `oot` | zeldawiki | GFDL 1.3 | 51 | 952 |
| `zelda1` | zeldawiki | GFDL 1.3 | 39 | 803 |
