# API HTTP

FastAPI expone el pipeline compartido con los evaluadores. Un benchmark directo del pipeline no incluye transporte HTTP, renderizado de Gradio ni interacción del navegador. Los comandos siguientes se ejecutan desde la raíz después de la [instalación con Python 3.12 y uv](../../README.md).

```powershell
uv run --no-sync python -m gamerag.bootstrap
uv run --no-sync uvicorn gamerag.api:app --reload
```

La documentación interactiva está en `http://127.0.0.1:8000/docs`. Al iniciar se construye el pipeline y se cargan perfiles locales. La sección `configuration` de `/health` permite comprobar opciones efectivas sin mostrar credenciales.

| Método y ruta | Función | Acceso de demostración |
| --- | --- | --- |
| `GET /health` | Estado, configuración efectiva y juegos | Consulta |
| `GET /games` | Juegos, modelos de progreso y disponibilidad de índices | Consulta |
| `GET /profiles`, `GET /profiles/{user_id}` | Perfiles sembrados | Consulta |
| `POST /ask` | Respuesta, evidencia final y traza opcional | Perfil conocido |
| `POST /search` | Recuperación autorizada sin generación | Perfil conocido |
| `GET /scorecard` | Métricas de artefactos persistidos | Consulta |
| `GET /audit` | Auditoría sanitizada | Rol `admin` |
| `POST /admin/reset-profiles` | Restablecer perfiles | Rol `admin` |
| `POST /admin/purge-audit` | Aplicar retención de auditoría | Rol `admin` |

## Consulta

```json
{
  "question": "How can I sail across the sea?",
  "game": "zelda1",
  "user_id": "completionist",
  "include_trace": true
}
```

`AskResponse.answer` conserva los campos académicos y las extensiones existentes. `AskResponse.evidence` devuelve la evidencia autorizada exacta; cada documento contiene `source`, `page`, `chunk_id`, `url`, `section`, `version`, `source_hash`, `text`, `is_excerpt` y `evidence_hash`. `include_trace` es `true` por defecto; al desactivarlo, `trace` y `explanation` son `null`, pero `evidence` sigue disponible. La explicación resume la ruta y las decisiones de la traza.

La interfaz abre citas desde `evidence`, sin lanzar otra búsqueda. Una llamada independiente a `/search` sirve para explorar recuperación, pero puede diferir del contexto final después de una reescritura o búsqueda secundaria. Sus hits conservan el ordinal real `page`; esta ruta devuelve siempre su traza, sin ejecutar herramientas ni generación y sin persistir una fila de auditoría.

## Errores y límites

| Código | Condición |
| --- | --- |
| 403 | Operación administrativa con rol insuficiente |
| 404 | Perfil desconocido, juego no disponible o scorecard aún inexistente |
| 422 | Entrada inválida: longitud, identificador o esquema |
| 429 | Límite de solicitudes por usuario excedido |

Los errores internos y degradaciones se distinguen en las trazas. La aplicación limita llamadas de herramientas y solicitudes por minuto. La selección de un `user_id` no acredita identidad: esta API se utiliza como demostración local, según [ADR-0004](../architecture/decisions/0004-sqlite-and-demo-profiles.md).

## Auditoría

SQLite conserva perfiles y una fila de auditoría por llamada completada a `/ask`, incluidas abstenciones y rechazos del pipeline. Las entradas rechazadas por validación HTTP no llegan al registro. La traza incluye respuesta y evidencia finales, etapas, llamadas LLM y degradaciones. La respuesta HTTP distingue `question`, la entrada original, de `clean_question`, la versión utilizada después de los controles; la auditoría sanitiza sus campos textuales antes de persistirlos. La retención es configurable. Véanse [contratos](../contracts/pipeline.md) y [datos sensibles](../data/sensitive-data.md).
