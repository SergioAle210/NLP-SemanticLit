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
