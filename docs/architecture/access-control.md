# Control de acceso y protección de spoilers

El acceso combina el juego activo, el perfil y la clasificación del contenido. Se aplica antes de generar, sobre búsquedas primarias, secundarias y filas de herramientas. Los perfiles locales son una demostración de política, sin autenticación de identidad.

## Capas vigentes

| Capa | Regla | Alcance |
| --- | --- | --- |
| Aislamiento de juego | `chunk.game` coincide con el juego solicitado | También para usuarios sin restricciones de progreso |
| Ubicación | Misma quest y nivel completado o actual; en juegos lineales, etapa anterior o actual | `LocationGate` y configuración por juego |
| Fuente no clasificada | Contenido marcado `restricted` no se entrega a jugadores limitados | Fuentes adicionales sin ubicación fiable |
| Política de contenido | Proyectar secciones, pasajes o filas permitidas | `ContentPolicy`, reglas curadas en YAML |
| Procedencia | Una nota derivada depende del acceso a sus fuentes | Notas experimentales, desactivadas por defecto |
| Citas | Triple exacto fuente/página/chunk dentro de evidencia final | `CitationGuard` |
| Cuarentena | No utilizar como evidencia un original sospechoso | Se evalúa antes de proyectar |

Los perfiles `completionist` y `admin` no restringen el progreso, pero mantienen aislamiento de juego, controles de entrada, cuarentena y contrato de salida. Un jugador sin progreso del juego no adquiere acceso a todas sus ubicaciones.

La quest se deriva de títulos y encabezados, incluidas variantes `1st`, `2nd`, `First`, `Second` y `Quest 2`, y se hereda por subsecciones. La política vuelve a comprobar esos marcadores al recuperar para evitar que un corpus preparado con metadatos anteriores trate una sección de Second Quest como contenido general de First Quest.

## Contenido agregado y proyecciones

Una página sin ubicación explícita puede contener soluciones posteriores. `ContentPolicy` combina `content_rules`, `level_list_rules`, `map_sources` y `map_cell_rules` con la clasificación de secciones y tablas del corpus conocido:

- En Zelda, Silver Arrows y sus referencias requieren el progreso correspondiente al nivel final.
- Las listas de tesoros se proyectan según los niveles autorizados; las páginas Items y Overworld no se bloquean completas cuando contienen información separable.
- En los mapas Hyrule 1–8, cada celda se conserva como unidad. Las referencias a `dungeon` o `level`, mediante números, ordinales, listas o rangos, exigen acceso a todos los niveles citados. Las dependencias indirectas de Lost Hills, Spectacle Rock y el embarcadero se clasifican por celda y quest. La celda de White Sword y sus cinco corazones permanecen disponibles para `novato`; `Section 5` no se interpreta como mazmorra 5.
- Las páginas agregadas de jefes producen filas autorizadas de nombre, HP, daño y aparición. Las tácticas ubicadas en cada mazmorra siguen la política de su ubicación.
- El recorrido agregado `/Walkthrough` de Zelda exige que todos los niveles estén en el conjunto de completados o nivel actual de la quest del jugador, porque mezcla dependencias entre zonas.
- En Ninja Gaiden, los desenlaces de batallas requieren una etapa posterior; las tácticas del tramo actual se conservan cuando la segmentación permite separarlas.
- Una ventana fija que corta una sección sensible recibe un tratamiento conservador. En mapas, también se descartan los bordes de celdas sin límites verificables en ventanas estructurales o por fila pequeñas; las celdas completas autorizadas del mismo fragmento se conservan.

Antes de cualquier proyección se comprueba el original contra aislamiento de juego y cuarentena. La proyección conserva `source`, `page`, `chunk_id` y `version`; `source_hash` identifica el original y `evidence_hash` el texto autorizado. `is_excerpt` señala que la evidencia es parcial.

La cuarentena identifica su caché por el hash del texto. Un fragmento revisado no hereda una decisión permisiva solo por conservar el mismo `chunk_id`. Los patrones incluyen notas dirigidas a asistentes o modelos en inglés y español; su alcance sigue siendo heurístico.

## Límites

La política es curada sobre el corpus conocido. Las dependencias indirectas deben revisarse al incorporar fuentes o modificar mapas; la protección de Hyrule no equivale a un clasificador semántico universal de spoilers. Tampoco implementamos una escala completa de pistas progresivas. El campo histórico `hint_level` del perfil no se presenta en la interfaz como una capacidad activa.

Los nombres G1, G2, G2b, G3 y G4 aparecen en los ADRs como etapas del diseño inicial. La implementación actual combina aislamiento, ubicación y reglas de contenido; no debe afirmarse que todas las etapas originales estén implementadas por completo.

## Verificación

La prueba de fuga debe utilizar expectativas independientes de `LocationGate` y `ContentPolicy`. Comprobar únicamente que el contexto pasó el mismo filtro no detecta errores de clasificación. Se incluyen casos de páginas generales, soluciones finales, narración posterior, filas de herramientas, fuentes adicionales y citas falsificadas. Los resultados y su configuración están en [seguridad](../security/report.md).
