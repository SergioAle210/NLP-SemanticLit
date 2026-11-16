# Problema, alcance y criterios de éxito

GameRAG ayuda a localizar una respuesta documental sin revisar guías completas que pueden revelar contenido posterior al progreso del jugador. La pregunta se restringe al juego activo y a evidencia autorizada; las respuestas deben conservar citas o abstenerse.

## Usuario y contexto

El usuario principal es un jugador que consulta una mecánica, objeto, ubicación o enemigo. Los perfiles con progreso limitado necesitan evitar soluciones posteriores; `completionist` acepta el corpus completo del juego. El administrador de demostración inspecciona auditoría. Los perfiles se seleccionan por identificador y no constituyen autenticación real.

Una respuesta incorrecta puede provocar tiempo perdido, instrucciones inaplicables, mezcla entre quests o exposición a spoilers. El sistema opera como demostración académica y no modifica partidas, archivos del videojuego ni servicios externos.

## Alcance actual

La configuración incluye siete juegos. La evaluación principal concentra 54 casos históricos en The Legend of Zelda y Ninja Gaiden (NES); los demás se incorporan mediante bancos y fuentes adicionales. El idioma principal evaluado es inglés.

Incluye ingesta de wikis versionadas, BM25, embeddings E5, RRF, expansión de consulta, generación extractiva/Haiku, grafo acotado, herramientas de lectura, FastAPI, Gradio y auditoría SQLite. Las fuentes adicionales sin clasificación suficiente permanecen restringidas a jugadores con progreso limitado.

No incluye autenticación de producción, ejecución de acciones críticas, aprobación persistente de cambios de progreso, memoria conversacional ni una garantía universal contra spoilers. Planificación y notas documentales son opciones experimentales. Las pistas graduadas completas no están implementadas.

## Metas del proyecto

| Dimensión | Meta | Interpretación |
| --- | --- | --- |
| Hit rate@5 | ≥ 0.80 | Consultas con alguna evidencia relevante; informar además recall por unidades de evidencia y su denominador |
| Precisión de citas | ≥ 0.90 | Distinguir relevancia documental de apoyo factual |
| Abstención global correcta | ≥ 0.90 | Proporción de decisiones correctas entre los casos evaluables |
| Sensibilidad de abstención | ≥ 0.90 | Proporción de casos no respondibles en los que se abstiene; no evaluable si el banco carece de ellos |
| Operación | P95 < 6 s | Declarar equipo, configuración y caché |
| Spoilers | Cero fugas en la suite definida | Oráculo independiente; no garantía sobre todas las consultas |
| Contrato | Respuestas estructuradas | Evidencia y trazas de la misma consulta |

Estas metas son decisiones del proyecto; el curso exige evaluación cuantitativa y cualitativa sin convertir sus ejemplos numéricos en umbrales universales. Los [resultados](../course/informe-final.md) muestran metas aún no alcanzadas en todas las configuraciones.
