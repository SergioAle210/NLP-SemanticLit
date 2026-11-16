# Despliegue local y Docker

La configuración vigente sirve FastAPI en el puerto 8000 y Gradio en el puerto 7860. Compose utiliza una imagen para ambos servicios y Chroma embebido en la API.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
```

La copia inicial de `.env` es opcional y se realiza una sola vez. `docker compose down` detiene los servicios conservando los volúmenes. La opción `-v` elimina los volúmenes y sus datos; no es necesaria para una parada ordinaria.

| Servicio | Puerto | Función |
| --- | --- | --- |
| `api` | 8000 | Bootstrap del corpus y arranque de Uvicorn |
| `ui` | 7860 | Puesto de Control; consulta `http://api:8000` |

La interfaz espera el healthcheck de la API. En el primer inicio semántico se descarga el modelo si no existe en caché; los siguientes reutilizan modelos e índices. Compose carga `.env` en el servicio `api`; la URL interna y la dirección de escucha de Gradio se definen en `compose.yaml`.

## Preparación reproducible

Se requiere uv y Python 3.12, fijado en `.python-version`. `uv sync` prepara el entorno `.venv` del proyecto; no debe ejecutarse el proyecto con un Python global anterior, como Python 3.7. Los comandos se ejecutan desde la raíz del repositorio.

```powershell
uv sync --locked --extra semantic --extra ui
uv run --no-sync python -m gamerag.bootstrap
uv run --no-sync uvicorn gamerag.api:app
```

`gamerag.bootstrap` utiliza `Settings`: juegos seleccionados, rutas, chunker y búsqueda secundaria. Prepara los primarios y, cuando corresponde, los conjuntos `-multi`. Calcula una huella de configuración, snapshots y lógica de ingesta para reutilizar artefactos vigentes o reconstruirlos. Publica cada archivo atómicamente y el manifiesto de validación al final; comunica errores de preparación. No descarga fuentes o modelos ni llama al LLM. Uvicorn carga los índices al arrancar; el arranque local requiere ejecutar el bootstrap después de modificar fuentes o configuración.

El perfil `base` utiliza generación extractiva. `full` requiere una clave no vacía para activar el preset de grafo, Haiku, evaluación de evidencia y recuperación secundaria; la generación remota requiere que el proveedor acepte la clave. Una clave vacía se normaliza como ausente. Sin clave, `profile` conserva el valor solicitado `full`, pero el preset no se aplica: el bootstrap muestra `full_without_key=true` y `/health.configuration` permite comprobar las opciones efectivas. Cualquier opción explícita conserva prioridad sobre el preset.

## Persistencia

| Volumen | Ruta | Contenido |
| --- | --- | --- |
| `models` | `/app/models` | Caché de modelos |
| `index` | `/app/data/index` | Índices y metadatos |
| `processed` | `/app/data/processed` | Chunks y huellas de ingesta |
| `state` | `/app/state` | Perfiles, auditoría y estado local |

El índice debe invalidarse ante cambios de texto, revisión o metadatos. Las credenciales se inyectan al arrancar y no forman parte de la imagen. El corpus contiene varias fuentes y licencias; la [gobernanza](../data/sources.md) se mantiene también al redistribuir una imagen.

## Verificaciones registradas

Se verificó un arranque limpio con generación de corpus primario y adicional para los siete juegos. La configuración de comprobación fue `GAMERAG_PROFILE=full`, override `GAMERAG_RETRIEVER=bm25`, clave ficticia inválida y `GAMERAG_LLM_OFFLINE=true`. El grafo y la búsqueda secundaria estuvieron activos; no se utilizaron credenciales válidas ni llamadas remotas.

El [registro HTTP](../../eval/results/2026-11-16_http-closure-offline.json) conserva 36/36 comprobaciones de aquella configuración y verifica `llm_offline` en `/health` antes de consultar. Incluye citas, hashes de evidencia, respuesta final y ausencia de llamadas remotas. Es un registro anterior a la corrección posterior de celdas de Hyrule; no se presenta como una nueva ejecución del código actual ni como medición de calidad o latencia de Haiku. Las verificaciones posteriores se distinguen en la [auditoría](../evaluation/audit-current.md). La [interfaz](../ui/README.md) fue inspeccionada por separado en el navegador.
