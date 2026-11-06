# Despliegue con Docker

Levanta la API y la interfaz sin instalar Python, uv ni PyTorch.

```bash
cp .env.example .env            # opcional: ANTHROPIC_API_KEY
docker compose up --build       # API: http://localhost:8000/docs · interfaz: http://localhost:8501
docker compose down             # detener (los volúmenes se conservan)
docker compose down -v          # detener y borrar volúmenes (modelos, índice, perfiles, auditoría)
```

## Servicios

| Servicio | Puerto | Qué corre |
| --- | --- | --- |
| `api` | 8000 | Si faltan chunks, corre la ingesta; luego levanta `uvicorn gamerag.api:app` ([entrypoint](../../scripts/docker-entrypoint.sh)) |
| `ui` | 8501 | Streamlit ([ui/](../ui/README.md)). Espera a que la API pase el healthcheck y le habla por `http://api:8000` |

Los dos servicios usan **una sola imagen** (`gamerag:latest`). **ChromaDB no tiene servicio propio:** corre embebido dentro de la API y guarda archivos en `data/index/`.

## Volúmenes

| Volumen | Ruta en el contenedor | Contenido | Primer arranque |
| --- | --- | --- | --- |
| `models` | `/app/models` | Modelo de embeddings (`multilingual-e5-small`) | Se descarga (~470 MB) |
| `index` | `/app/data/index` | Índice de Chroma | Se construye (segundos) |
| `processed` | `/app/data/processed` | Chunks de la ingesta | Se generan (segundos) |
| `state` | `/app/state` | SQLite: perfiles y auditoría | Se siembran los 5 perfiles |

El primer arranque tarda por la descarga del modelo; los siguientes reutilizan los volúmenes. Si cambia el texto indexado (`INDEX_TEXT_VERSION`), el índice se reconstruye solo.

## Decisiones

- **La imagen es reproducible:**
  - `uv sync --locked` instala exactamente las versiones de `uv.lock`;
  - uv y Python están fijados a una versión;
  - PyTorch sale del índice CPU (sin CUDA, mucho más liviano).
- **Credenciales fuera de la imagen:** `.env` está en `.dockerignore` y se inyecta en tiempo de ejecución (`env_file`, opcional). Sin API key, el sistema usa el generador extractivo.
- **Lo que no entra a la imagen:**
  - los manuales (`data/raw/`), porque tienen copyright;
  - los artefactos regenerables (modelos, índices, chunks), que van en volúmenes;
  - los tests y la documentación.
- **El corpus sí va en la imagen:** son los snapshots de StrategyWiki (CC BY-SA 4.0), unos 400 KB.
- **Healthcheck:** la interfaz arranca solo cuando `/health` responde, así no muestra "API no disponible" durante el primer arranque.
