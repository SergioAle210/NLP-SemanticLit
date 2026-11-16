# Datos sensibles y auditoría

El corpus contiene texto público de wikis. La entrada libre del usuario puede contener información personal o secretos, por lo que su tratamiento se define de forma independiente a la licencia del corpus.

| Dato | Ubicación | Tratamiento |
| --- | --- | --- |
| Snapshot y manifiestos | `data/wiki_snapshot/` | Atribución, revisión y clasificación de contenido |
| Pregunta | Memoria de la solicitud, traza HTTP y auditoría | Versión redactada antes de recuperación y LLM; sanitización al persistir |
| Perfil | SQLite y semilla de demostración | Identificador, rol y progreso; sin autenticación real |
| Respuesta y evidencia final | Traza y auditoría | Sanitización antes de persistir |
| Clave del proveedor | Entorno local | No incluir en repositorio, configuración pública ni logs |
| Caché y costos | `state/` | Estado local excluido del control de versiones |

## Minimización y redacción

`PIIGuard` sustituye patrones detectables de correos, teléfonos, tarjetas, identificadores y secretos. La recuperación y el modelo reciben `clean_question`; la traza HTTP conserva además `question` con la entrada original para el mismo solicitante. La auditoría aplica una segunda sanitización a sus campos textuales antes de persistirlos. El contexto entregado al modelo contiene evidencia autorizada y la pregunta redactada; no necesita enviar el perfil completo ni credenciales del usuario.

La redacción basada en patrones no detecta todos los nombres, direcciones o datos personales. Una cifra histórica favorable de falsos positivos o sondas de acceso se refiere a un banco y configuración específicos; no constituye una garantía universal sobre información sensible.

## Persistencia y acceso

La retención se configura mediante `audit_retention_days`, con 90 días por defecto y `0` para conservar el registro, y se aplica al arranque o desde la ruta administrativa de purga. Se registran las llamadas completadas a `/ask`; `/search` no escribe auditoría. Los endpoints de auditoría requieren rol administrativo en la demostración. Como el cliente selecciona el `user_id`, ese control no sustituye autenticación para un servicio público.

La traza persistida conserva pregunta sanitizada, decisiones, respuesta final, evidencia, llamadas y degradaciones. Si se redacta el texto de evidencia, se indica mediante `audit_redacted` y `recorded_text_hash`, manteniendo la identidad y los hashes de procedencia. La caché LLM guarda respuestas del proveedor sin cifrado, bajo un nombre derivado del hash de la solicitud; no guarda el prompt como contenido del archivo. El ledger registra consumo y costo estimado. Estos artefactos locales no se distribuyen con el código.

## Gobernanza documental

Las fuentes mantienen URL, revisión y licencia declarada. Los snapshots se actualizan manualmente y se reevalúan después de cambios. Las notas documentales opcionales conservan procedencia y acceso derivado; no son memoria conversacional. Véanse [fuentes](sources.md), [contratos](../contracts/pipeline.md) y [seguridad](../security/controls.md).
