# ADR-0007: Diferencias entre juegos como configuración, no como código

**Estado:** aceptado (2026-11-05)

## Contexto

Los dos juegos difieren en el modelo de progreso, en dónde está la ubicación dentro de la wiki y en las herramientas que tienen sentido ([overview/games.md](../../overview/games.md)).

## Decisión

Todo lo que distingue a un juego vive en `config/games/<game_id>.yaml`, validado por `src/gamerag/games.py`:

| Campo | Zelda | Ninja Gaiden |
| --- | --- | --- |
| `progress_model` | `level_set` | `linear_stage` |
| `levels` / `quests` / `stages` | 1-9 / first, second | 21 etapas, en orden |
| `location_from_title` | `Underworld/Quest (?P<quest>\d)/Dungeon (?P<level>\d)` | `Act (?P<act>\d)` |
| `location_from_heading` | — | `(?:Stage\|Act) (?P<stage>\d-\d)` |
| `exclude_pages` | Índice de navegación | Índice de navegación |
| `tools` | Incluye `next_available_levels` | Sin grafo |
| `aliases` | — | Shadow Warriors, Ninja Ryukenden |

La validación rechaza configuraciones incoherentes, por ejemplo una herramienta de grafo en un juego lineal.

## Alternativas consideradas

- **Condicionales por juego en el código** (`if game == "zelda1"`). Dispersa la lógica y vuelve costoso agregar un juego.

## Consecuencias

- El pipeline (ingesta, gates, router) es genérico; agregar un juego es escribir un YAML.
- Los tests verifican la config contra el corpus real: las expresiones regulares encuentran las 18 mazmorras de Zelda y las 21 etapas de Ninja Gaiden.
