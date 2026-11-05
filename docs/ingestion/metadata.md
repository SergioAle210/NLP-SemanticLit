# Metadatos del chunk

Implementación: [src/gamerag/ingest/models.py](../../src/gamerag/ingest/models.py) y [location.py](../../src/gamerag/ingest/location.py).

## Esquema

| Campo | Ejemplo | Para qué |
| --- | --- | --- |
| `chunk_id` | `zelda1:underworld-quest-1-dungeon-4:001` | Identificador estable: `juego:página:n` (mínimo del curso) |
| `text` | `[Boss]\nThe boss is a two headed Gleeok...` | Contenido (mínimo del curso) |
| `source` | `The Legend of Zelda/Underworld/Quest 1/Dungeon 4` | Página de origen (mínimo del curso) |
| `page` | `3` | Índice de la sección donde empieza (mínimo del curso; en la wiki no hay páginas físicas) |
| `version` | `revid:1125348` | Revisión exacta de la página (mínimo del curso) |
| `url` | `https://strategywiki.org/wiki/...` | Enlace para verificar la cita |
| `section` / `sections` | `Objectives > Dungeon Walkthrough` | Sección donde empieza / todas las que abarca |
| `hash` | `sha256:6c15...` | Detecta cambios de contenido entre ingestas |
| `chunker` | `fixed-w225-o30` | Estrategia y parámetros (comparabilidad entre ingestas) |
| `n_words` | `225` | Tamaño |
| `lang` | `en` | Idioma del texto |
| `game` | `zelda1` | Gate G1 |
| `location` | `{"quest": "first", "level": 4, "act": null, "stage": null}` | Gates G2 y G2b ([access-control.md](../architecture/access-control.md)) |

`location` con todos los campos en `null` significa **contenido general**, visible sin restricción de ubicación: controles, objetos, enemigos.

## Derivación de la ubicación

Se usan las expresiones regulares de la config del juego ([ADR-0007](../architecture/decisions/0007-per-game-config.md)):

| Juego | Fuente | Expresión | Resultado |
| --- | --- | --- | --- |
| Zelda | Título de la página | `Underworld/Quest (?P<quest>\d)/Dungeon (?P<level>\d)` | `quest` "1" → `first` (según el orden de `quests` en la config), `level` 4 |
| Ninja Gaiden | Título de la página | `Act (?P<act>\d)` | `act` 2 |
| Ninja Gaiden | Encabezados de la sección | `(?:Stage\|Act) (?P<stage>\d-\d)` | `stage` "2-3" (gana el encabezado más profundo que coincida) |

## Pendiente (fase 3)

- `entities`: entidades mencionadas (gate G3).
- `hint_tier`: nivel de detalle (gate G4).
- `premise`: el contenido proviene del manual o de la sección "Story" (ignora G3).
- `segment` (Ninja Gaiden): `intro`, `stage`, `boss` u `outro` (gate G2b).
