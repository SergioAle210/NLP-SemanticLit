# Pipeline de ingesta

Cubre el §5.3 de [course/instructions.md](../course/instructions.md): carga, extracción, limpieza, chunking, metadatos e indexación. El corpus vigente incluye siete juegos y varias licencias; el inventario está en [fuentes](../data/sources.md).

```text
data/wiki_snapshot/<fuente>/<juego>/pages/*.wiki   (snapshot versionado, licencia por fuente)
  │  manifest.json: título, URL y revid de cada página
  ▼
clean.py      wikitext -> texto plano (plantillas, enlaces, tablas)        -> cleaning.md
  ▼
sections.py   texto -> secciones con ruta jerárquica de encabezados
  ▼
chunking.py   secciones -> ventanas fijas, estructurales o por fila           -> chunking.md
  ▼
location.py   ubicación en el juego según la config (quest/level, act/stage) -> metadata.md
  ▼
build.py      arma los Chunk (models.py) y escribe JSONL + estadísticas
  ▼
data/processed/<juego>/chunks.fixed.jsonl   (regenerable, fuera de git)
data/processed/<juego>/stats.fixed.json
  ▼
índices (BM25 / Chroma)   -> retrieval/
```

## Uso

Preparación recomendada según el perfil efectivo:

```bash
uv run --no-sync python -m gamerag.bootstrap
```

El bootstrap prepara los juegos configurados, genera primarios y conjuntos `-multi` cuando la búsqueda secundaria los requiere, comprueba huellas de configuración/snapshots/ingesta y publica cada artefacto atómicamente, con el manifiesto de validación al final. Una preparación explícita de ambos conjuntos para los siete juegos produjo 2,759 chunks primarios y 10,462 chunks multifuente en la revisión de cierre. Las estadísticas de cada corrida identifican su contenido concreto; la proyección de contenido autorizado ocurre al recuperar y no reescribe estos originales.

Para experimentos de segmentación individuales:

```bash
uv run --no-sync python -m gamerag.ingest.build zelda1
uv run --no-sync python -m gamerag.ingest.build ninja_gaiden_nes
uv run --no-sync python -m gamerag.ingest.build zelda1 --chunker structural
uv run --no-sync python -m gamerag.ingest.build zelda1 --chunker structural --sources all
uv run --no-sync python -m gamerag.ingest.build zelda1 --size 300 --overlap 50
```

El comando imprime las estadísticas y escribe los archivos en `data/processed/<juego>/`. El CLI experimental toma sus parámetros de segmentación de los argumentos y escribe el mismo nombre por estrategia, aunque cambie `--size`; el bootstrap vuelve a preparar la configuración de servicio predeterminada si esos archivos no coinciden con su huella. No debe interpretarse una salida experimental sobrescrita como la ingesta validada del servicio.

## Experimento histórico de segmentación inicial

Conservamos estas cifras del corpus primario inicial de Zelda y Ninja Gaiden; no representan el total actual de siete juegos ni una nueva ejecución con las reglas de contenido.

| | Zelda fijo | Zelda estructural | NG fijo | NG estructural |
| --- | ---: | ---: | ---: | ---: |
| Páginas usadas / snapshot | 40 / 41 | 40 / 41 | 10 / 11 | 10 / 11 |
| Chunks | 153 | 243 | 70 | 84 |
| Palabras por chunk (mín / media / máx) | 37 / 200.9 / 225 | 7 / 110.2 / 225 | 36 / 209.9 / 225 | 31 / 152.5 / 221 |
| Chunks que cruzan secciones | 94 (61%) | 22 (9%) | 32 (46%) | 0 (0%) |
| Chunks con ubicación | 66 | 112 | 59 | 69 |
| Plantillas desconocidas | 0 | 0 | 0 | 0 |

La línea base usa el chunking fijo; la fase 3, el estructural ([chunking.md](chunking.md)).

La página excluida en cada juego es el índice de navegación (`exclude_pages` en la config).

## Propiedades garantizadas por tests

Están en [tests/test_ingest.py](../../tests/test_ingest.py), con el corpus primario de los juegos configurados y fixtures específicos:

- No quedan restos de marcado (`{{`, `[[`, `{|`, `'''`, `<br`) en las páginas primarias incluidas por la configuración.
- Una lista de **hechos de referencia** del wikitext sobrevive a la limpieza: precios, ficha del juego, filas de tablas, coordenadas de mapas, frases de los ancianos y escenas de Ninja Gaiden. Los fixtures se conservan en tests; no equivalen a una revisión humana nueva del corpus completo. Ver [cleaning.md](cleaning.md#validación-histórica-contra-el-original).
- No hay plantillas sin regla en ese corpus primario; las fuentes adicionales conservan su propio conteo en las estadísticas.
- La ingesta es **determinista**: dos ejecuciones producen exactamente los mismos chunks.
- Los `chunk_id` son únicos.
- Cada una de las 18 mazmorras de Zelda (9 por quest) tiene chunks con su ubicación.
- Las ventanas respetan el tamaño y el solapamiento, cubren todas las palabras y conservan los saltos de línea.

Las pruebas de [fuentes adicionales](../../tests/test_multisource.py) comprueban separación de identidades y restricciones por defecto. Las de [contenido](../../tests/test_content_policy.py) verifican la proyección posterior de mapas, tablas y narración, incluidas ventanas que cortan celdas.

## Documentos

- [cleaning.md](cleaning.md): reglas de limpieza y casos especiales.
- [chunking.md](chunking.md): estrategia, parámetros y limitaciones.
- [metadata.md](metadata.md): esquema del chunk y derivación de la ubicación.
