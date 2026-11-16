# Hoja de ruta y estado de entrega

Esta hoja distingue capacidades implementadas de la evidencia necesaria para declarar la entrega cerrada. Los resultados históricos se preservan en `eval/results/` y sus documentos; la revisión de cierre no convierte esas corridas en evaluaciones de código posterior.

| Fase del curso | Entregable disponible | Verificación y límite |
| --- | --- | --- |
| Anteproyecto | [Documento de 16 secciones](course/informe.md), alcance, riesgos y diagramas | Consolidación documental realizada a partir del repositorio; no se presenta como registro fechado antes de implementar |
| Línea base | BM25, segmentación fija, generador extractivo y banco estructurado | Comparaciones históricas conservadas con configuración y banco |
| Mejora técnica | Segmentación estructural, E5, RRF, expansión, Haiku y grafo acotado | El perfil `full` requiere comprobar clave, corpus y configuración efectiva; planificador y notas permanecen opcionales |
| Herramientas | Router, SQL de lectura, consulta de progreso y derivación de acciones críticas | Las acciones críticas y cambios de progreso no se ejecutan; no hay circuito completo de aprobación y modificación |
| Evaluación | Bancos de recuperación, generación, herramientas, versiones y seguridad; scorecard | Diferenciar banco de desarrollo, conjunto ya inspeccionado y revisión humana pendiente; comparar ejecuciones del mismo esquema |
| Seguridad | Validaciones, filtros, cuarentena, citas, PII y límites | Los controles de spoilers dependen de la clasificación del corpus; las pruebas no acreditan cobertura semántica universal |
| Documentación | [Informe final](course/informe-final.md), contratos, README y [guion](course/defensa.md) | Fuente formal, PDF A4 y dos diagramas; manifiesto de páginas y hashes por exportación |
| Defensa | Guion y casos de demostración | Ensayo, exposición individual y revisión humana de respuestas corresponden al equipo; no se declaran realizados sin registro |

## Evidencia conservada del cierre previo

La corrida base conservada cubre 136 consultas sin errores ni llamadas LLM. En el banco principal obtiene hit rate@5 de 0.9388 y precisión de citas de 0.3061; la pérdida de un acierto frente a la corrida intermedia queda registrada. La suite de seguridad obtiene 37/42, con cinco fallas de abstención extractiva. El oráculo de contenido obtiene 7/9 con dos fallas de utilidad, mientras el aislamiento de quests y las dos revisiones documentales sintéticas superan sus casos. Estas mediciones preceden al refuerzo de celdas y rutas en mapas de Hyrule; no son benchmarks nuevos del código posterior ni equivalen a alcanzar todas las metas.

## Verificaciones completadas

| Verificación | Evidencia y alcance |
| --- | --- |
| Suite posterior al refuerzo de mapas | 520 pruebas aprobadas, sin omisiones, verificadas en consola; no se generó otro XML |
| Registro automatizado del cierre previo | [489 pruebas, 0 omitidas](../eval/results/2026-11-16_pytest-closure.xml), en 30.51 s; Ruff aprobado en ese cierre. Las repeticiones focales no se suman al total de la suite |
| Corpus e índices | El cierre previo generó siete juegos, 2,759 chunks primarios y 10,462 multifuente; existen pruebas de actualización de revisión y metadatos |
| Despliegue limpio previo | Docker preparó primario y adicional; preset full, override BM25, clave ficticia inválida y modo offline |
| Contrato HTTP previo | [36/36 comprobaciones](../eval/results/2026-11-16_http-closure-offline.json), con verificación previa de `llm_offline`, sin llamadas remotas ni costo |
| Mapas de Hyrule | Proyección de celdas y rutas implementada; siete comprobaciones HTTP posteriores verificadas en consola, sin nuevo JSON |
| Gradio | En el cierre previo se inspeccionaron consulta, citas, Dodongo, búsqueda, scorecard y contraste oscuro; los cambios visuales posteriores no convierten esa inspección en una nueva validación completa |
| Evaluación | Artefactos de esquema 2 del cierre previo, seguridad y herramientas; se conservan metas incumplidas y su procedencia |

La revisión humana de fidelidad y relevancia, el recorrido completo de accesibilidad y el ensayo de defensa no se acreditan como realizados. Las nuevas corridas `full` requieren credenciales y presupuesto. Cada exportación del informe debe conservar su manifiesto y pasar la verificación visual y de 10–15 páginas.

## Trabajo futuro

La autenticación real, la actualización de progreso con aprobación persistente, la curaduría exhaustiva de spoilers en todas las fuentes, la evaluación extensa en español y una nueva evaluación de herramientas con frases no vistas quedan fuera de la versión académica actual. Una memoria conversacional requeriría reglas de conservación y acceso distintas de las notas documentales experimentales.

Los experimentos descartados —reranker general, segmentación global por filas, planificación y notas en la configuración principal— permanecen documentados. Su eventual reincorporación requiere una mejora medida sobre bancos comparables, junto con latencia, costo y riesgo de acceso.
