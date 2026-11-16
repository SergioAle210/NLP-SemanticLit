#!/bin/sh
# Arranque de la API: prepara los corpus requeridos por la configuración efectiva y levanta uvicorn.
# El modelo de embeddings se descarga a models/ y el índice de Chroma se construye en data/index/
# la primera vez; los dos quedan en volúmenes y se reutilizan en los siguientes arranques.
set -e

python -m gamerag.bootstrap

exec uvicorn gamerag.api:app --host 0.0.0.0 --port 8000
