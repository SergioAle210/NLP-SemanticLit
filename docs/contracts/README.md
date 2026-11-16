# Contratos entre componentes

Los contratos se validan con Pydantic y protocolos de Python. Las definiciones ejecutables son la referencia para tipos y valores permitidos.

| Contrato | Documento | Implementación |
| --- | --- | --- |
| Fragmento, ubicación y versión | [Metadatos](../ingestion/metadata.md) | `ingest/models.py` |
| Generación y salida académica | [Generación](generation.md) | `generation/base.py`, `schemas.py` |
| Perfiles, acceso y guardrails | [Acceso](access-and-guardrails.md) | `progress/models.py`, `guardrails/` |
| Consulta, evidencia y traza | [Pipeline](pipeline.md) | `pipeline.py`, `api.py` |
| Herramientas | [Router y herramientas](../tools/README.md) | `tools/` |

`Source` conserva `source`, `page` y `chunk_id`. `Answer` conserva los campos exigidos por el curso: `answer`, `sources`, `abstained`, `tool_used` y `needs_human_review`, además de las extensiones `game`, `blocked_by_spoiler` y `trace_id`.

La respuesta HTTP incorpora `evidence` como extensión aditiva. Cada documento conserva la identidad de `Source` y añade URL, sección, versión, hash del fragmento original, texto autorizado, indicador de extracto y hash de evidencia. Una proyección que oculta parte de un fragmento conserva su identidad documental y distingue el texto entregado del texto original mediante ambos hashes.
