# Pipeline de ingesta

Cubre el §5.3 de [course/instructions.md](../course/instructions.md): carga, extracción, limpieza, chunking, metadatos e indexación.

```text
data/wiki_snapshot/<fuente>/<juego>/pages/*.wiki   (snapshot versionado, CC BY-SA 4.0)
  │  manifest.json: título, URL y revid de cada página
  ▼
clean.py      wikitext -> texto plano (plantillas, enlaces, tablas)        -> cleaning.md
  ▼
sections.py   texto -> secciones con ruta jerárquica de encabezados
  ▼
chunking.py   secciones -> ventanas de tamaño fijo (línea base)             -> chunking.md
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

```bash
uv run python -m gamerag.ingest.build zelda1
uv run python -m gamerag.ingest.build ninja_gaiden_nes
uv run python -m gamerag.ingest.build zelda1 --chunker structural      # chunking de la fase 3
uv run python -m gamerag.ingest.build zelda1 --size 300 --overlap 50   # otros parámetros
```

El comando imprime las estadísticas y escribe los archivos en `data/processed/<juego>/`.

## Resultado actual

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

Están en [tests/test_ingest.py](../../tests/test_ingest.py):
- No quedan restos de marcado (`{{`, `[[`, `{|`, `'''`, `<br`) en ninguna página del corpus.
- Una lista de **hechos verificados a mano** contra el wikitext original sobrevive a la limpieza: precios, ficha del juego, filas de tablas, coordenadas de mapas, frases de los ancianos, escenas de Ninja Gaiden. Ver la validación en [cleaning.md](cleaning.md#validación-contra-el-original).
- No hay plantillas sin regla.
- La ingesta es **determinista**: dos ejecuciones producen exactamente los mismos chunks.
- Los `chunk_id` son únicos.
- Cada una de las 18 mazmorras de Zelda (9 por quest) tiene chunks con su ubicación.
- Las ventanas respetan el tamaño y el solapamiento, cubren todas las palabras y conservan los saltos de línea.

## Documentos

- [cleaning.md](cleaning.md): reglas de limpieza y casos especiales.
- [chunking.md](chunking.md): estrategia, parámetros y limitaciones.
- [metadata.md](metadata.md): esquema del chunk y derivación de la ubicación.
