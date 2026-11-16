# Fuentes y gobernanza

El corpus vigente contiene snapshots de siete juegos y varias wikis. La configuración ejecutable se encuentra en [config/sources.yaml](../../config/sources.yaml) y las asociaciones de cada juego en [config/games/](../../config/games/). El [inventario de snapshots](../../data/wiki_snapshot/README.md) conserva cantidades y atribución.

| Fuente | Formato | Atribución | Licencia declarada |
| --- | --- | --- | --- |
| StrategyWiki | Wikitext / JSON | Colaboradores de la página | CC BY-SA 4.0 |
| Wikipedia | Wikitext / JSON | Colaboradores del artículo | CC BY-SA 4.0 |
| Grand Theft Wiki | Wikitext / JSON | Colaboradores del sitio | CC BY-SA 3.0 |
| Fandom: Assassin's Creed, Doom, GTA, Ninja Gaiden y Red Dead | Wikitext / JSON | Colaboradores de cada wiki | CC BY-SA; versión no siempre indicada por API |
| Zeldapedia | Wikitext / JSON | Colaboradores de la wiki | GFDL |
| Zelda Wiki | Wikitext / JSON | Colaboradores de la wiki | GFDL 1.3 |

La tabla reproduce la información registrada en los snapshots y su configuración. No implica que todos los textos tengan una licencia común ni reemplaza la revisión de condiciones antes de redistribuir derivados. Las fuentes GFDL se mantienen separadas y atribuidas; la licencia MIT corresponde al código.

## Adquisición, versión y actualización

`scripts/download_wiki.py` obtiene páginas de StrategyWiki y `scripts/fetch_corpus.py` prepara las fuentes configuradas. Cada carpeta conserva `pages/*.wiki` y `manifest.json`, con título, URL, revisión y tamaño. La fecha de descarga corresponde al manifiesto, no a una fecha inventada de publicación.

La actualización es manual. Una descarga nueva puede cambiar revisiones, por lo que el snapshot versionado identifica la referencia experimental. Después de cambiar contenido o metadatos se reconstruyen chunks e índices y se repite la evaluación afectada. El bootstrap calcula huellas y evita reutilizar artefactos obsoletos.

La frecuencia operativa se define por hitos para todas las fuentes de la tabla: conservamos congeladas las revisiones durante una campaña de evaluación y revisamos la necesidad de una nueva descarga antes de la siguiente campaña o cuando se detecta una corrección relevante. No ejecutamos sondeos periódicos ni actualizaciones automáticas. Esta política especifica cuándo considerar una revisión; no afirma que se haya realizado una descarga nueva en cada ejecución local.

## Acceso y tratamiento

Las páginas públicas pueden contener información que el jugador no desea ver. Los metadatos de juego y progreso, la restricción de fuentes sin clasificación y la política de contenido determinan la evidencia autorizada. Las fuentes de toda una franquicia no se incorporan por defecto a la búsqueda secundaria.

Los manuales comerciales no forman parte del corpus distribuido ni del pipeline de ingesta actual; algunas configuraciones conservan su URL como referencia histórica. No se versionan credenciales, perfiles locales, bases de auditoría, cachés ni índices regenerables. Las consultas pueden contener datos personales, aunque el corpus sea público; su tratamiento se describe en [datos sensibles](sensitive-data.md).
