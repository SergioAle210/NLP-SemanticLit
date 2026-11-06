#!/bin/sh
# Arranque de la API en Docker: genera los chunks que falten (ingesta, segundos) y levanta uvicorn.
# El modelo de embeddings se descarga a models/ y el índice de Chroma se construye en data/index/
# la primera vez; los dos quedan en volúmenes y se reutilizan en los siguientes arranques.
set -e

CHUNKER="${GAMERAG_CHUNKER:-structural}"
for cfg in config/games/*.yaml; do
    game="$(basename "$cfg" .yaml)"
    if [ ! -f "data/processed/$game/chunks.$CHUNKER.jsonl" ]; then
        echo "[entrypoint] ingesta de $game ($CHUNKER)"
        python -m gamerag.ingest.build "$game" --chunker "$CHUNKER"
    fi
done

exec uvicorn gamerag.api:app --host 0.0.0.0 --port 8000
