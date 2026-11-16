# Pipeline, evidencia y traza

La API y los evaluadores reutilizan `build_pipeline(settings)`. `ask(question, game, profile)` devuelve respuesta y traza; `search` realiza recuperación autorizada sin generación. Una búsqueda independiente no representa necesariamente el contexto final de una consulta que activó reescritura o fuentes secundarias.

## Etapas y decisiones

| Etapa | Salida o manejo de error |
| --- | --- |
| Entrada | Validación, redacción de PII y rechazo de instrucciones adversarias |
| Router | Ruta documental, herramienta permitida o acción que requiere revisión |
| Herramienta | Parámetros y filas validadas; excepción o timeout degrada al RAG |
| Recuperación | Rankings y variantes de consulta; candidatos con score |
| Acceso | Evidencia permitida, proyectada o bloqueada según perfil |
| Generación | Respuesta estructurada; degradación extractiva ante fallo |
| Evidencia en grafo | Revisión y recuperación adicional bajo límite de reescrituras |
| Salida | Contrato, identidad de citas y controles de filtración |
| Auditoría | Respuesta final, evidencia, decisiones y operación sanitizadas |

Por defecto se solicitan hasta 50 candidatos para seleccionar hasta 5 fragmentos autorizados; ambos valores son configurables. La profundidad interna de RRF es estable y puede limitar la cantidad efectiva de candidatos. La unión del planificador opcional y la búsqueda secundaria en modo `append` pueden ampliar el contexto; el preset `full` usa `mixed`, que lo reemplaza por hasta `secondary_k` fragmentos autorizados. El código distingue `answered`, `abstained`, `blocked_by_access`, `rejected_input`, `rejected_output` y `retrieved`.

## Evidencia exacta de la respuesta

`AskResponse` contiene `answer`, `trace` cuando se solicita y `evidence`. Cada elemento de evidencia contiene:

| Campo | Significado |
| --- | --- |
| `source`, `page`, `chunk_id` | Identidad de cita compatible con `Source` |
| `url`, `section`, `version` | Enlace, encabezado y revisión documental |
| `source_hash` | SHA256 del fragmento fuente antes de proyectarlo, con prefijo `sha256:` en el corpus generado |
| `text` | Texto autorizado exacto disponible al responder |
| `is_excerpt` | Indica que se entregó una proyección parcial |
| `evidence_hash` | SHA256 hexadecimal del texto de evidencia entregado, sin prefijo |

La interfaz usa estos datos para abrir una cita. `SearchHit.page` mantiene el ordinal real de sección en la ruta de búsqueda. Ninguna de estas extensiones altera los campos obligatorios de `Answer` ni la identidad de `Source`.

## Traza

| Grupo | Campos y finalidad |
| --- | --- |
| Identidad y entrada | `trace_id`, `question` original, `clean_question` tras controles, juego, usuario y rol |
| Configuración | Recuperador, generador y variantes de consulta |
| Decisión | `route`, `route_reason`, herramienta y sus parámetros/estado |
| Recuperación | `candidates`, score, rank, bloqueo y `context` |
| Validación | Guardrails de entrada/salida y resultado final |
| Evidencia final | `final_evidence` y `final_answer`, correspondientes a la respuesta entregada |
| Operación | `llm_calls`, `degradations`, `stages` y `latency_ms` |

Las etapas conservan el orden real de ejecución, incluidas búsquedas adicionales. Las llamadas LLM se atribuyen a la consulta para no mezclar telemetría concurrente. La recuperación y el generador usan `clean_question` cuando está disponible; `question` conserva la entrada original en la traza devuelta al solicitante. La auditoría sanitiza los campos textuales antes de persistir y puede reconstruir la representación registrada de la respuesta y su evidencia sin volver a ejecutar el recuperador. Los identificadores de fragmentos retenidos no autorizan a mostrar su contenido.

La evidencia de la API conserva el texto autorizado exacto. Si la auditoría redacta un extracto, preserva hashes de procedencia y versión y asigna `audit_redacted=true` y `recorded_text_hash` para identificar la representación guardada; en la respuesta HTTP ordinaria esos campos tienen los valores `false` y `null`. La persistencia corresponde a `/ask`; `/search` devuelve su traza sin guardarla.
