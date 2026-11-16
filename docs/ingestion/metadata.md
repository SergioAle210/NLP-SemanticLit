# Metadatos del fragmento

El modelo ejecutable se encuentra en [ingest/models.py](../../src/gamerag/ingest/models.py). Preserva los cinco campos obligatorios del curso y añade trazabilidad y acceso.

| Campo | Uso |
| --- | --- |
| `text` | Texto del fragmento o de su proyección autorizada |
| `source` | Título de página, con origen cuando corresponde |
| `page` | Ordinal de la sección donde comienza; no página impresa |
| `chunk_id` | Identificador reproducible dentro de juego, fuente y configuración de ingesta |
| `version` | `revid` documental |
| `url`, `section`, `sections` | Enlace y ruta de encabezados |
| `hash` | SHA256 del texto del fragmento |
| `chunker`, `n_words`, `lang` | Segmentación, tamaño e idioma |
| `game`, `origin` | Aislamiento y procedencia |
| `location` | Quest, nivel, acto, etapa y restricción explícita |
| `kind`, `derived_from` | Fuente o nota experimental y dependencias |
| `is_excerpt`, `source_hash` | Proyección autorizada y hash del original |

`location` se deriva de títulos y encabezados según configuración. La ausencia de una ubicación no demuestra que el texto carezca de spoilers. Las fuentes adicionales sin clasificación se marcan como restringidas salvo una excepción general explícita en su configuración; la política de contenido puede proyectar secciones, filas y celdas de páginas agregadas.

La quest se reconoce tanto en títulos Overworld/Quest como en encabezados `1st/2nd`, `First/Second` o `Quest 2`, y se hereda por las subsecciones. La comprobación de contenido repite esa restricción como defensa frente a artefactos preparados con reglas anteriores.

## Identidad, revisión y evidencia

La quest es una variante del juego; `version` es la revisión documental. Una cita se identifica por el triple `source/page/chunk_id` y se verifica contra el contexto final. Los IDs se reproducen con las mismas entradas y estrategia, pero pueden cambiar al alterar la segmentación o el orden del contenido; no son una identidad permanente entre todas las revisiones. Cambios de revisión, URL, ubicación o restricciones invalidan la representación persistida incluso si el texto no cambia.

Al proyectar un fragmento se mantienen identidad, URL y revisión. `source_hash` conserva el hash original y `hash` se recalcula sobre el extracto; ambos usan el prefijo `sha256:` en los chunks generados. La evidencia HTTP incorpora además `evidence_hash`, el digest hexadecimal sin prefijo del texto exacto. Las proyecciones se realizan después de comprobar juego y cuarentena del original. Véanse [acceso](../architecture/access-control.md) y [contrato de evidencia](../contracts/pipeline.md).

No se añaden campos ficticios `entities`, `hint_tier` o `segment` para representar capacidades todavía no implementadas. Las reglas curadas actuales residen en la configuración del juego.
