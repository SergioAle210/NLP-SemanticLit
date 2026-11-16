# Contratos de acceso y guardrails

`Profile` contiene `user_id`, rol y progreso por juego. Los roles son `player`, `completionist` y `admin`; los dos últimos tienen acceso sin restricción de progreso. El campo histórico `hint_level` se conserva por compatibilidad, sin prometer un sistema completo de pistas graduadas.

`LevelSetProgress` registra quest, niveles completados y nivel actual. `LinearStageProgress` registra la etapa actual, interpretada mediante el orden de la configuración. `validate_profile` rechaza juegos, quests, niveles o etapas incompatibles.

## Acceso

`AccessFilter.allows(chunk, profile, game) -> bool` verifica un candidato. Los filtros de juego, ubicación, cuarentena y procedencia se aplican antes de utilizar contenido. La política de contenido puede producir un extracto autorizado conservando identidad y revisión del original.

Una proyección no puede convertir un original de otro juego o en cuarentena en evidencia permitida. Los hashes de origen y evidencia permiten distinguir el fragmento fuente de la parte entregada. El [control de acceso](../architecture/access-control.md) documenta reglas y límites.

## Entrada y salida

`InputGuard.check(question, profile)` y `OutputGuard.check(answer, context, profile)` producen una decisión con motivo y señales. Un rechazo de entrada termina sin recuperación. Un rechazo de salida sustituye el resultado por abstención y revisión humana.

| Control | Responsabilidad |
| --- | --- |
| `BasicInputGuard` | Longitud y contenido no vacío |
| `InjectionGuard` | Patrones de instrucciones adversarias |
| `PIIGuard` | Redacción de datos detectables antes del procesamiento |
| `QuarantineFilter` | Retención de originales sospechosos |
| `CitationGuard` | Juego y triple `source/page/chunk_id` contra evidencia autorizada |
| `LeakGuard` | Indicadores de filtración de instrucciones o secretos |

La identidad correcta de una cita no demuestra respaldo factual. La evaluación de fidelidad compara las afirmaciones con el texto exacto entregado; los controles de seguridad se evalúan con casos independientes de sus reglas.
