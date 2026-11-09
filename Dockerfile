# Imagen única para la API (FastAPI) y la interfaz (Streamlit). Ver docs/deployment/README.md.
FROM python:3.12-slim

# uv fijado a una versión exacta (misma que se usa en desarrollo).
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Dependencias (capa cacheada mientras no cambien pyproject.toml / uv.lock).
#    --locked: exactamente las versiones de uv.lock. Torch sale del índice CPU (sin CUDA).
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra semantic --extra ui --no-install-project

# 2) Código, configuración y corpus (los snapshots de la wiki van en el repo; CC BY-SA 4.0).
COPY src ./src
COPY config ./config
COPY data/wiki_snapshot ./data/wiki_snapshot
COPY data/seed ./data/seed
COPY eval ./eval
COPY scripts/docker-entrypoint.sh ./scripts/docker-entrypoint.sh
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra semantic --extra ui

# Artefactos regenerables (montados como volúmenes en compose.yaml).
RUN mkdir -p models data/index data/processed state

EXPOSE 8000 7860
CMD ["sh", "scripts/docker-entrypoint.sh"]
