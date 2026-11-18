## 1. Información general

Título del proyecto: GameRAG: asistente documental para videojuegos con control de spoilers por progreso.

Integrantes:

- Sergio Orellana, 221122.
- Ricardo Chuy, 221007.
- Rodrigo Mansilla, 22611.

Dominio: recuperación de información y asistencia documental sobre videojuegos.

Usuario primario: jugadores que necesitan resolver una duda sin conocer anticipadamente contenido posterior a su progreso.

## 2. Resumen ejecutivo

Proponemos un asistente para jugadores que necesitan resolver dudas sobre videojuegos sin conocer contenido posterior a su progreso. Atendemos la dispersión de información entre guías, la identificación de la revisión consultada y la exposición a soluciones anticipadas. Combinamos coincidencias de palabras y semejanzas de significado para recuperar evidencia del juego y del avance seleccionados. Utilizamos esa información para redactar respuestas verificables o indicar que no contamos con respaldo suficiente, e incorporamos consultas estructuradas sobre hechos y progreso. Esperamos reducir el esfuerzo de búsqueda y facilitar la comprobación de las respuestas mediante citas. Evaluaremos la recuperación, la generación, la operación y la seguridad, distinguiendo el estudio principal de The Legend of Zelda y Ninja Gaiden para NES de la ampliación exploratoria a otros cinco juegos.

## 3. Problema

### Situación actual

Identificamos que las guías distribuyen información relacionada entre páginas de objetos, mapas, enemigos y recorridos. Para resolver una pregunta, podemos necesitar reconocer nombres equivalentes, distinguir variantes de la partida y reunir información de varias secciones. Al abrir una guía completa, encontramos tanto el contenido necesario como soluciones que todavía no deseamos conocer.

### Dolor o limitación

Buscamos reducir el esfuerzo de localizar y comprobar información sin depender de conocimientos que el modelo no pueda respaldar. Consideramos errores relevantes mezclar juegos, atribuir una solución a una versión incorrecta o citar una página que no sostiene la respuesta. Aunque una guía sea pública, debemos evaluar si su contenido corresponde al avance del jugador.

### Impacto

Reconocemos como consecuencias el tiempo perdido al seguir instrucciones incorrectas, la interrupción de la experiencia de juego y la revelación irreversible de contenido. Delimitamos nuestro estudio a la confianza en las respuestas y al respeto de las preferencias del jugador dentro de una demostración académica.

### Pregunta principal del sistema

Formulamos la pregunta central así: ¿qué respuesta podemos ofrecer utilizando exclusivamente evidencia del juego activo, compatible con el progreso del jugador y acompañada de fuentes que permitan verificarla?

## 4. Usuario y contexto

| Usuario | Necesidad | Permisos | Riesgo de error |
| --- | --- | --- | --- |
| Jugador con progreso limitado | Resolver una duda del tramo alcanzado | Contenido del juego y del avance registrados | Revelar soluciones, acontecimientos o ubicaciones posteriores |
| Jugador que acepta spoilers | Consultar toda la información disponible del juego | Contenido sin restricción por progreso | Recibir una respuesta incorrecta o mezclar versiones |
| Administrador de la demostración | Revisar decisiones y configuración | Registros locales y operaciones administrativas | Exponer datos registrados o modificar información por error |
| Equipo evaluador | Reproducir y explicar el comportamiento | Casos de prueba, copias documentales y resultados | Confundir una prueba parcial con una garantía general |

Utilizamos perfiles predefinidos que reúnen el juego, la variante de la partida, el avance y la aceptación de spoilers. Permitimos seleccionarlos durante la demostración, pero no verificamos la identidad de quien los utiliza. Antes de un despliegue público, necesitaremos vincular esos permisos con un mecanismo de autenticación.

## 5. Objetivos

### Objetivo general

Nos proponemos diseñar e implementar un sistema de recuperación y generación fundamentada que responda preguntas sobre videojuegos con evidencia verificable, restricciones según el progreso y evaluación reproducible.

### Objetivos específicos

1. Preparar las fuentes mediante un procedimiento reproducible que conserve el texto, su procedencia, la sección, la revisión y las restricciones de acceso.
2. Comparar la búsqueda léxica BM25 con la búsqueda híbrida y justificar cómo dividimos, representamos y ordenamos la información.
3. Producir respuestas con citas comprobables y mecanismos de abstención cuando la evidencia sea insuficiente.
4. Distinguir entre preguntas documentales, consultas de hechos o progreso y solicitudes de cambio que requieren revisión.
5. Medir la recuperación, el respaldo de las respuestas, la cobertura, la abstención, la latencia y el costo, indicando los casos considerados en cada cálculo.
6. Documentar las fallas, los límites de cobertura y el uso de herramientas de inteligencia artificial durante el desarrollo.

## 6. Alcance

### Incluye

Incluimos copias textuales de wikis, consultas principalmente en inglés, dos formas de dividir los documentos y búsqueda por palabras y significado. Ofrecemos respuestas mediante extracción de texto o mediante un modelo de lenguaje, una interfaz de consulta, perfiles de progreso y registros locales de las decisiones del sistema.

Configuramos siete juegos: The Legend of Zelda, Ninja Gaiden para NES, The Legend of Zelda: Ocarina of Time, Assassin's Creed II, Doom, Grand Theft Auto: San Andreas y Red Dead Redemption. Concentramos la evaluación principal y la clasificación inicial del contenido en los dos primeros. Estudiaremos la cobertura de los otros cinco por separado, pues su incorporación no demuestra un nivel equivalente de validación.

### No incluye

Excluimos automatizar la partida, modificar el estado del videojuego y ofrecer autenticación para un servicio público. Tampoco prometemos detectar cualquier spoiler ni ofrecer resultados equivalentes en todos los idiomas. No distribuimos manuales comerciales como parte de la colección. Ante solicitudes de cambiar el progreso o los permisos, indicamos la necesidad de revisión y conservamos el estado registrado.

### MVP

Definimos el producto mínimo viable como una consulta sobre un juego que recupere evidencia de una copia documental, produzca una respuesta con formato verificable y presente al menos una cita válida. También requerimos un mecanismo activo de abstención o bloqueo. Compararemos las mejoras de búsqueda y del flujo de decisión con esta referencia para valorar su aporte y su costo.

## 7. Fuentes y gobernanza

| Fuente | Formato | Propietario | Actualización | Permiso | Sensibilidad |
| --- | --- | --- | --- | --- | --- |
| StrategyWiki | Texto de wiki y metadatos estructurados | Colaboradores de cada página | Manual por campaña de evaluación | Lectura; CC BY-SA 4.0 declarada | Pública |
| Wikipedia | Texto de wiki y metadatos estructurados | Colaboradores de cada artículo | Manual por campaña de evaluación | Lectura; CC BY-SA 4.0 declarada | Pública |
| Grand Theft Wiki | Texto de wiki y metadatos estructurados | Colaboradores del sitio | Manual por campaña de evaluación | Lectura; CC BY-SA 3.0 declarada | Pública |
| Wikis especializadas de Fandom | Texto de wiki y metadatos estructurados | Colaboradores de cada wiki | Manual por campaña de evaluación | Lectura; CC BY-SA según la versión disponible | Pública |
| Zeldapedia y Zelda Wiki | Texto de wiki y metadatos estructurados | Colaboradores de cada wiki | Manual por campaña de evaluación | Lectura; GFDL o GFDL 1.3 declarada | Pública |

Conservamos la dirección de origen, el título y el número de revisión de cada página. Asociamos a cada fragmento una huella digital del texto que permite detectar cambios, además de su procedencia y ubicación dentro del documento. Antes de redistribuir materiales derivados, debemos comprobar la atribución y las condiciones de cada fuente; no asignamos una licencia uniforme a toda la colección.

Tratamos de manera restrictiva las fuentes cuya clasificación resulta insuficiente para un perfil limitado. Podemos autorizar información general mediante reglas explícitas del juego, pero no suponemos que una página completa carezca de spoilers. Separamos las fuentes sobre franquicias y las excluimos por defecto de las búsquedas complementarias. Cuando cambia una revisión o un dato de procedencia, debemos actualizar la representación utilizada para buscar, aunque el texto visible permanezca igual.

## 8. Requisitos

### Funcionales

1. Validar la pregunta, el juego y el perfil antes de iniciar la consulta.
2. Recuperar información del juego activo y aplicar las restricciones antes de redactar la respuesta.
3. Responder con evidencia suficiente o indicar expresamente que no podemos hacerlo.
4. Presentar una respuesta estructurada que incluya las citas, la abstención, la función utilizada y la necesidad de revisión cuando corresponda.
5. Mostrar la evidencia exacta que respalda la respuesta y la revisión documental de la que procede.
6. Registrar las decisiones, el contexto autorizado, la respuesta final y los cambios a una modalidad de funcionamiento limitada.
7. Rechazar acciones críticas sin modificar el progreso ni los permisos.

### No funcionales

1. Reproducir el entorno con versiones fijas de dependencias, copias documentales identificadas y procedimientos de preparación definidos.
2. Medir la latencia media y su percentil 95, las unidades de texto procesadas por el modelo, las solicitudes al proveedor y el costo estimado.
3. Limitar las consultas a funciones externas, los reintentos y el presupuesto del modelo de lenguaje.
4. Ocultar datos sensibles detectables en la preparación de consultas y en los registros persistentes, con un período de conservación configurable.
5. Mantener una modalidad que extraiga texto de las fuentes cuando no utilicemos generación remota e informar cuándo recurrimos a ella por una falla.

## 9. Arquitectura

### Flujo de la solución

Organizamos la consulta documental en una secuencia de validación, identificación de la intención, recuperación, autorización de evidencia, generación y comprobación de la respuesta. Para una pregunta que requiere datos estructurados, consultamos únicamente los registros permitidos y comprobamos la salida sin recurrir al generador. En la preparación del corpus, extraemos el texto, lo limpiamos, reconocemos sus secciones y lo dividimos en fragmentos que conservan sus datos de procedencia.

### Componentes

| Componente | Función | Entrada | Salida | Justificación |
| --- | --- | --- | --- | --- |
| Preparación documental | Normalizar y dividir las fuentes | Copias de páginas y datos de procedencia | Fragmentos asociados a una revisión | Reproducir la información utilizada |
| Búsqueda | Localizar evidencia pertinente | Pregunta y juego | Fragmentos ordenados | Combinar coincidencias de palabras y semejanza de significado |
| Filtros de acceso | Restringir el contenido | Fragmentos y perfil | Evidencia autorizada | Respetar el juego, la variante y el progreso |
| Clasificación y consultas estructuradas | Seleccionar cómo resolver la solicitud | Intención y datos de la pregunta | Hechos, progreso o solicitud de revisión | Separar información documental y estado del jugador |
| Generación | Redactar o extraer una respuesta | Pregunta y evidencia permitida | Respuesta con campos definidos | Facilitar su comprobación |
| Validación de salida | Comprobar formato y citas | Respuesta y evidencia | Respuesta aceptada o abstención | Rechazar estructuras o referencias inválidas |
| Interfaz | Recibir consultas y mostrar resultados | Solicitud del usuario | Respuesta, citas y explicación | Facilitar la demostración |
| Auditoría | Conservar las decisiones | Registro con datos sensibles ocultos | Historial local | Analizar errores y reproducir evaluaciones |

En la configuración completa representamos el procesamiento como un flujo de decisión con estados y transiciones explícitos. Podemos revisar la evidencia y repetir la búsqueda dentro de un límite. Definimos previamente las funciones disponibles y las condiciones para utilizarlas; no delegamos al modelo la autorización de nuevas acciones.

## 10. Recuperación y RAG

### Estrategia de chunking

Dividimos los documentos de dos maneras. Como referencia, utilizamos ventanas de hasta 225 palabras con un solapamiento de 30. Para el servicio, respetamos los encabezados y agrupamos líneas completas y secciones pequeñas; cuando una línea supera el máximo, la dividimos por palabras.

### Metadatos

Conservamos la fuente, la sección, el identificador, la revisión, la dirección de origen, la huella del texto y las restricciones de cada fragmento. En las páginas de wiki, identificamos la ubicación mediante el orden de la sección, no mediante una página impresa.

### Modelo de embeddings

Representamos el significado de preguntas y fragmentos mediante el modelo multilingüe E5 de tamaño pequeño, que produce vectores de 384 valores. Distinguimos las preguntas de los pasajes al preparar esas representaciones. Fundamentamos esta elección en Wang et al. (2024), la documentación de Intfloat y la comparación local de recuperadores.

### Índice

Persistimos vectores y metadatos en Chroma y calculamos similitud exacta sobre los vectores cargados. Mantenemos además un índice léxico BM25. Reconstruimos las representaciones ante cambios en el texto, la revisión o las restricciones de acceso.

### Búsqueda

Combinamos BM25 y similitud semántica mediante fusión recíproca de rangos, siguiendo a Cormack, Clarke y Büttcher (2009). Sumamos las contribuciones de las posiciones con una constante de 60 y el mismo peso para cada lista. Consideramos correcciones ortográficas y nombres equivalentes de un glosario, y filtramos los candidatos por juego y progreso antes de utilizarlos.

### Reranking

Conservamos como comparación experimental un modelo que valora conjuntamente la pregunta y cada fragmento. No lo activamos por defecto porque no hemos demostrado una mejora suficiente en los bancos utilizados; utilizamos el orden producido por la fusión de resultados.

### Citas

Aplicamos generación aumentada por recuperación a partir del planteamiento de Lewis et al. (2020). Entregamos al modelo únicamente evidencia autorizada y comprobamos que cada cita corresponda a la fuente, la sección y el fragmento utilizados. Mostramos el texto exacto y su revisión documental para facilitar la verificación.

### Abstención

Rechazamos respuestas sin evidencia autorizada o con referencias inválidas. En el modo generativo podemos revisar la suficiencia documental y buscar información complementaria dentro de un número limitado de intentos. No consideramos una puntuación de búsqueda como garantía de respaldo semántico. Evaluaremos por separado las preguntas no respondibles, para las que fijamos una meta de detección de al menos 90 %.

## 11. Herramientas y agentes

| Herramienta | Propósito | Parámetros | Permisos | Validación |
| --- | --- | --- | --- | --- |
| Consulta de hechos del juego | Enumerar datos estructurados sobre jefes de The Legend of Zelda | Variante de la partida y nivel | Lectura de registros autorizados | Rangos válidos, límite de resultados y citas |
| Consulta de progreso | Mostrar niveles registrados y por completar | Perfil y juego | Lectura del perfil seleccionado | Coherencia con el progreso y las reglas del juego |
| Solicitud de actualización | Reconocer una petición de cambiar el progreso | Cambio solicitado | Sin ejecución automática | Necesidad de revisión y conservación del estado |
| Solicitud crítica | Detectar borrado, modificación de permisos o desbloqueo | Acción solicitada | Sin ejecución automática | Rechazo o revisión |
| Consulta documental | Responder preguntas informativas | Pregunta y evidencia | Acceso solo a información autorizada | Formato, citas y suficiencia documental |

Utilizamos funciones estructuradas cuando necesitamos enumerar más hechos de los que caben en el contexto documental o consultar el estado del jugador. Obtenemos el progreso del perfil seleccionado, no de una wiki. Al mostrar niveles por completar, describimos lo que falta en ese registro; no calculamos todos los prerrequisitos necesarios para completarlos durante una partida.

## 12. Evaluación

### Banco de pruebas

Cantidad de casos: partimos de 54 consultas, con 39 de The Legend of Zelda y 15 de Ninja Gaiden. Incluimos 8 preguntas directas, 5 paráfrasis, 5 consultas de nombres exactos, 4 preguntas compuestas, 2 ambiguas, 4 etiquetadas como no respondibles, 3 sobre variantes y 23 de robustez.

Fuentes esperadas: asociamos cada consulta con pasajes de las guías del juego y con los registros estructurados cuando utilizamos herramientas. Conservamos pregunta, condiciones de acceso, respuesta o conducta esperada y evidencia necesaria para repetir la evaluación.

Casos sin respuesta: requerimos abstención en las cuatro consultas clasificadas como no respondibles y en un caso adicional de robustez. Comprobaremos la ausencia de evidencia suficiente y las solicitudes ajenas al dominio.

Casos de seguridad: conservamos conjuntos separados de ataques directos, instrucciones maliciosas en documentos, intentos de eludir permisos y solicitudes críticas. También probamos las restricciones por juego y progreso.

Evaluaremos los cambios entre revisiones documentales mediante ejemplos reales o controlados. No consideraremos las diferencias entre variantes de la partida o nombres regionales como sustitutos de una prueba de actualización de documentos.

### Métricas

Establecemos las siguientes metas como decisiones del proyecto. No las presentamos como resultados alcanzados ni como umbrales universales exigidos por el curso.

| Métrica | Definición | Meta | Método de cálculo |
| --- | --- | --- | --- |
| Acierto entre los cinco primeros resultados | Proporción de preguntas con al menos una evidencia pertinente en esas posiciones | Al menos 0.80 | Evaluar preguntas respondibles e indicar cuántas se consideran |
| Cobertura de evidencia esperada | Proporción de partes esperadas que recuperamos | Mejorar la referencia | Comparar con la evidencia definida para cada caso; no equivale a recuperar todos los documentos pertinentes de la colección |
| Rango recíproco medio | Promedio del inverso de la posición de la primera evidencia pertinente | Mejorar la referencia | Comparar sobre el mismo banco de preguntas |
| Precisión de citas | Proporción de citas pertinentes entre las emitidas | Al menos 0.90 | Comparar con la evidencia esperada; comprobar por separado identidad y respaldo de las afirmaciones |
| Fidelidad | Grado en que la evidencia final respalda las afirmaciones | Identificar errores y desacuerdos | Utilizar un evaluador automático y proponer una revisión humana de una muestra |
| Abstención | Corrección global de la decisión y detección de preguntas no respondibles | Al menos 0.90 en cada indicador | Contar aciertos y errores; no calcular la detección si el banco carece de preguntas no respondibles |
| Latencia en el percentil 95 | Tiempo dentro del cual terminan aproximadamente el 95 % de las consultas | Menos de 6 segundos en la configuración declarada | Identificar la corrida y el uso de respuestas almacenadas |
| Seguridad | Exposición de contenido prohibido e incumplimientos ante ataques | Cero fugas en el conjunto definido | Comparar con expectativas independientes de los filtros y probar entradas adversarias |

## 13. Seguridad

Inyección de instrucciones: validamos las entradas, detectamos patrones maliciosos conocidos y separamos el contenido documental de las instrucciones del sistema. Aislamos los textos sospechosos antes de utilizarlos como evidencia.

Documentos no autorizados: comprobamos el juego, el progreso y la procedencia, con atención especial a páginas que reúnen soluciones de distintas etapas. Los perfiles locales representan permisos de demostración y no sustituyen una identidad autenticada.

Información sensible: ocultamos correos, teléfonos y secretos detectables antes de transmitir consultas a servicios externos o conservar registros.

Herramientas peligrosas: limitamos las solicitudes y mantenemos las consultas estructuradas en modo de lectura. Derivamos los cambios de progreso y permisos a revisión, sin ejecutarlos.

Salidas inválidas: comprobamos el formato de la respuesta y la identidad de las citas contra la evidencia autorizada. Evaluamos por separado si esa evidencia respalda las afirmaciones.

Registros de auditoría: conservamos las decisiones, la evidencia autorizada y la respuesta final con los datos sensibles ocultos y un período de retención configurable. Aislamos los registros de consultas concurrentes.

## 14. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación | Prueba |
| --- | --- | --- | --- | --- |
| Spoilers en páginas que reúnen varias etapas | Alta | Alto | Clasificación conservadora y restricción de evidencia | Casos de objetos, ubicaciones y acontecimientos con expectativas independientes de los filtros |
| Recuperación insuficiente | Media | Alto | Búsqueda híbrida, ampliación de consultas y abstención | Medición de acierto, cobertura y posición de evidencia; análisis por caso |
| Cita válida que no respalda la afirmación | Media | Alto | Evaluación frente al contexto final | Revisión de fidelidad |
| Fuente o revisión desactualizada | Media | Medio | Registro de procedencia y actualización de representaciones | Reprocesamiento con cambios de revisión |
| Indisponibilidad del proveedor | Media | Medio | Presupuesto, reutilización de resultados y alternativa extractiva | Simulación de errores y tiempos de espera agotados |
| Clasificación de intención ajustada en exceso a los ejemplos | Alta | Medio | Conservar las fallas y utilizar un conjunto nuevo sin inspección previa | Evaluación antes de modificar las reglas |
| Confusión entre perfil local e identidad verificada | Alta fuera de la demostración | Alto | Restringir el alcance académico | Pruebas de acceso a operaciones administrativas |
| Atribución o licencia incompleta | Media | Alto | Separación por fuente y conservación de sus condiciones | Inspección antes de redistribuir |

## 15. Plan de trabajo

Organizamos la responsabilidad de forma colectiva y vinculamos cada fase con un entregable verificable. Indicamos el período mensual de trabajo, sin asignar días específicos ni responsabilidades individuales sin documentación.

| Fase | Actividad | Responsable | Entregable | Fecha |
| --- | --- | --- | --- | --- |
| Línea base | Preparación por ventanas, búsqueda BM25 y banco inicial | Equipo del proyecto | Implementación y métricas de referencia | Noviembre de 2026 |
| RAG | Segmentación por secciones, representación semántica, fusión y respuestas | Equipo del proyecto | Sistema integrado y comparación | Noviembre de 2026 |
| Herramientas | Clasificación de intención, hechos y progreso | Equipo del proyecto | Funciones y pruebas | Noviembre de 2026 |
| Evaluación | Métricas, revisiones documentales y fidelidad | Equipo del proyecto | Resultados comparables y análisis de fallas | Noviembre de 2026 |
| Seguridad | Ataques, permisos y clasificación de spoilers | Equipo del proyecto | Reporte y ejemplos reproducibles | Noviembre de 2026 |

## 16. Referencias

- Lewis, P., et al. (2020). [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401).
- Cormack, G. V., Clarke, C. L. A., y Büttcher, S. (2009). [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf).
- Wang, L., et al. (2024). [Multilingual E5 Text Embeddings: A Technical Report](https://arxiv.org/abs/2402.05672).
- Intfloat (s. f.). [Ficha del modelo multilingüe E5 de tamaño pequeño](https://huggingface.co/intfloat/multilingual-e5-small).
- LangChain (s. f.). [Documentación de LangGraph](https://docs.langchain.com/oss/python/langgraph/overview).
- Pydantic (s. f.). [Modelos y validación](https://pydantic.dev/docs/validation/latest/concepts/models/).
- Universidad del Valle de Guatemala. Instrucciones del proyecto final y presentación del curso CC3103, Procesamiento de Lenguaje Natural, ciclo 2-2026.
