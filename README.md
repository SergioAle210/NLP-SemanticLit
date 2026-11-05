# NLP-SemanticLit: asistente RAG para juegos retro con protección de spoilers

Proyecto final de **CC3103 Procesamiento de Lenguaje Natural** (UVG, ciclo 2-2026).

Un asistente que responde preguntas sobre juegos de NES (*The Legend of Zelda* y *Ninja Gaiden*) con citas verificables. Solo revela información de las partes del juego que el jugador ya alcanzó.

> 🚧 Fase 1 (anteproyecto). El plan completo está en [docs/PLAN.md](docs/PLAN.md).

## Instalación (desarrollo local)

Requisitos: **Python 3.12** y **[uv](https://docs.astral.sh/uv/)**.

```bash
# 1. Instalar uv (una sola vez)
#    Windows (PowerShell):  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
#    macOS / Linux:         curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Crear el entorno e instalar las dependencias (genera .venv/ y, la primera vez, uv.lock)
uv sync                       # núcleo: ingesta, BM25, API, LLM
uv sync --extra semantic      # + embeddings, ChromaDB, reranker (fase 3; torch solo-CPU)
uv sync --extra ui            # + Streamlit

# 3. Configurar credenciales
cp .env.example .env          # y completar ANTHROPIC_API_KEY

# 4. Correr los tests
uv run pytest
```

> `uv.lock` se commitea: garantiza que todo el equipo y la imagen Docker usen exactamente las mismas versiones.

## Estructura actual

| Ruta | Contenido |
| --- | --- |
| [docs/PLAN.md](docs/PLAN.md) | Plan del proyecto: alcance, arquitectura, evaluación, seguridad y fases |
| [docs/instructions-proy.md](docs/instructions-proy.md) | Requisitos oficiales del proyecto |
| [docs/presentation-proy.md](docs/presentation-proy.md) | Presentación del curso |
| [data/wiki_snapshot/](data/wiki_snapshot/README.md) | Corpus: snapshots de StrategyWiki (CC BY-SA 4.0) |
| [scripts/download_wiki.py](scripts/download_wiki.py) | Descarga reproducible del corpus vía la API de MediaWiki |
| [config/games/](config/games/) | Configuración por juego (modelo de progreso, ubicación, herramientas) |
| [src/gamerag/](src/gamerag/) | Paquete principal: `settings`, `games`, `schemas` (contrato de salida) y subpaquetes por componente |
| [tests/](tests/) | Tests (`uv run pytest`) |
| `state/` | Base SQLite local (perfiles, auditoría). El contenido está en `.gitignore` |

## Reproducir el corpus

```bash
python scripts/download_wiki.py "The Legend of Zelda" data/wiki_snapshot/strategywiki/zelda1
python scripts/download_wiki.py "Ninja Gaiden (NES)" data/wiki_snapshot/strategywiki/ninja_gaiden_nes
```

## Licencias

- **Código:** [MIT](LICENSE).
- **Corpus de la wiki** (`data/wiki_snapshot/`) y sus derivados: **CC BY-SA 4.0**, de los colaboradores de StrategyWiki. Ver la [atribución](data/wiki_snapshot/README.md).
- **Manuales oficiales:** © Nintendo. **No se incluyen** en el repositorio, porque se descargan localmente en `data/raw/`, que está excluido del control de versiones.
