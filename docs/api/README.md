# API HTTP

Implementación: [src/gamerag/api.py](../../src/gamerag/api.py) (FastAPI) y [src/gamerag/store.py](../../src/gamerag/store.py) (SQLite). Es el **backend único**: lo consumen la interfaz y, en la fase 4, la evaluación del sistema completo, así que lo que se mide es lo que se ve en la demo.

```bash
uv sync --extra semantic                      # la configuración servida usa la búsqueda híbrida
uv run python -m gamerag.ingest.build zelda1 --chunker structural
uv run python -m gamerag.ingest.build ninja_gaiden_nes --chunker structural
uv run uvicorn gamerag.api:app --reload       # http://127.0.0.1:8000/docs
```

Al arrancar, la API construye el pipeline **una sola vez** (cargar el modelo de embeddings toma segundos) y siembra los perfiles en SQLite si la base está vacía.

## Endpoints

| Método y ruta | Descripción | Acceso |
| --- | --- | --- |
| `GET /health` | Estado, juegos disponibles, recuperador y generador en uso | Libre |
| `GET /games` | Juegos con su modelo de progreso (`levels`/`quests` o `stages`) y si tienen índice cargado | Libre |
| `GET /profiles`, `GET /profiles/{user_id}` | Perfiles de demo | Libre |
| `POST /ask` | Pregunta → `Answer` (§11) + `Trace`. Se registra en el log de auditoría. Si el router elige una herramienta, `answer.tool_used` la nombra y la traza lleva `route` y `tool` ([tools/](../tools/README.md)) | `user_id` de un perfil |
| `POST /search` | Solo recuperación + filtros: el contexto que recibiría el generador. No genera, así que no consume tokens | `user_id` de un perfil |
| `GET /audit?user_id=…&limit=20` | Últimas trazas del log de auditoría | Rol `admin` |
| `POST /admin/reset-profiles?user_id=…` | Restablece los perfiles sembrados | Rol `admin` |

La documentación interactiva (OpenAPI), con los esquemas exactos y un formulario para probar cada endpoint, está en **`/docs`**.

### `POST /ask`

```json
{"question": "How can I sail across the sea?", "game": "zelda1", "user_id": "novato", "include_trace": true}
```

```json
{
  "answer": {
    "answer": "Most relevant excerpts from the sources (no generated summary):\n[1] ...",
    "sources": [{"source": "The Legend of Zelda/Items", "page": 24, "chunk_id": "zelda1:items:024"}],
    "abstained": false, "tool_used": null, "needs_human_review": false,
    "game": "zelda1", "blocked_by_spoiler": false, "trace_id": "4f1c…"
  },
  "trace": {"outcome": "answered", "candidates": ["…"], "context": ["…"], "latency_ms": {"retrieval": 32.8}}
}
```

La estructura de la traza está en [contracts/pipeline.md](../contracts/pipeline.md).

### Errores

| Código | Cuándo |
| --- | --- |
| 404 | Juego no disponible (sin índice) o perfil desconocido |
| 403 | Endpoint administrativo con un perfil que no es `admin` |
| 422 | Validación de entrada: pregunta vacía o de más de 500 caracteres; `game` o `user_id` con caracteres no permitidos |

## Control de acceso de demo

No hay login ([ADR-0004](../architecture/decisions/0004-sqlite-and-demo-profiles.md)): cada request indica el `user_id` de un perfil sembrado. El rol y el progreso de ese perfil determinan qué contenido puede recuperar el pipeline (gates) y si puede usar los endpoints administrativos.

## Estado persistente (SQLite)

`GAMERAG_STATE_DB`, por defecto `state/gamerag.sqlite3` (fuera de git; un volumen en Docker):

| Tabla | Contenido |
| --- | --- |
| `profiles` | Perfiles (JSON), sembrados desde `data/seed/profiles.json` |
| `audit` | Una fila por consulta: `trace_id`, fecha, usuario, juego, pregunta **redactada**, outcome y la traza completa |

**Redacción de PII en el log** (`redact_pii`): correos → `[EMAIL]`, teléfonos → `[PHONE]`, claves de API → `[SECRET]`. Es la garantía mínima de que lo obvio no llegue al log (§5.8). La detección completa de PII es parte del `InputGuard` de PII ([contracts/access-and-guardrails.md](../contracts/access-and-guardrails.md)).

## Nota técnica

`api.py` no usa `from __future__ import annotations`. Con esa importación, FastAPI no resuelve los alias de dependencias definidos dentro de `create_app`, los trata como parámetros de query y responde 422.
