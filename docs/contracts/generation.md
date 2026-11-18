# Contrato de generación

`Generator.generate(question, context, *, game, trace_id) -> Answer` recibe la pregunta sanitizada y una lista ordenada de evidencia previamente autorizada. El generador no selecciona permisos ni amplía el corpus por su cuenta.

| Salida | Regla |
| --- | --- |
| `answer` | Texto apoyado en el contexto; inglés es el idioma principal evaluado |
| `sources` | Triples exactos `source/page/chunk_id` de evidencia disponible |
| `abstained` | Indica que no existe respaldo suficiente para responder |
| `tool_used` | Identifica la herramienta determinista, cuando aplica |
| `needs_human_review` | Señala incertidumbre, degradación o acción no ejecutada |
| `game`, `trace_id` | Conservan el juego y el identificador de la consulta |
| `blocked_by_spoiler` | Diferencia una restricción de acceso de falta documental |

## Implementaciones

- `ExtractiveGenerator`: devuelve, por defecto, los primeros tres fragmentos, recortados a aproximadamente 400 caracteres cada uno, con citas y una indicación explícita de que no son un resumen generado. La evidencia conserva el contexto autorizado sin ese recorte de presentación. Se abstiene ante contexto vacío. Recuperar texto no demuestra que responda semánticamente a la pregunta.
- `HaikuGenerator`: construye contexto delimitado como datos, solicita JSON y transforma identificadores citados en fuentes del contexto. La validación del esquema y los guardrails se aplican también a esta salida.
- `FallbackGenerator`: permite degradar al extractivo ante error del generador principal y marca revisión humana. La traza debe identificar el motivo; una respuesta HTTP exitosa no implica éxito del proveedor.

La configuración efectiva y los límites se leen de `Settings`. La capa LLM registra caché, uso, errores y presupuesto; el reporte operativo debe distinguir intentos, llamadas reales y reutilización de respuestas. Los precios configurados se usan para estimar costo, sin asumir que equivalen a una factura.

El control de costo serializa comprobación, llamada y registro entre clientes que comparten el ledger dentro de un proceso. No garantiza coordinación entre procesos independientes ni una cuota real del proveedor: utiliza precios configurados y consumo estimado.

## Abstención y fidelidad

No se utiliza un umbral universal de similitud como prueba suficiente de respuesta: preguntas respondibles y no respondibles pueden obtener scores cercanos. La abstención semántica depende de la relación entre pregunta y evidencia. El perfil `full` puede revisar la suficiencia ante una abstención y volver a recuperar dentro de un presupuesto limitado.

La validación de citas comprueba identidad documental; no demuestra por sí sola que cada afirmación esté respaldada. La fidelidad requiere evaluar afirmaciones contra la evidencia final entregada, con revisión humana o un juez separado cuyo resultado se conserve. Véase [metodología](../evaluation/metrics.md).

Si falla el evaluador de evidencia, la implementación actual registra la degradación y asume suficiencia para continuar. Esa decisión no acredita que la evidencia baste. La [revisión ampliada](../course/auditoria-cumplimiento.md#revisión-ampliada-del-estado-actual) identifica esta condición y la falta de abstención semántica del extractivo como limitaciones, incluidas las consultas que llegan a él por degradación.
