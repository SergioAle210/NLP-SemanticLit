# Anteproyecto consolidado: GameRAG

## 1. Información general

**Título:** GameRAG: asistente documental para videojuegos con control de spoilers por progreso.

**Curso:** CC3103, Procesamiento de Lenguaje Natural.

**Institución:** Universidad del Valle de Guatemala.

**Ciclo:** 2-2026.

**Docente:** Luis Esturbán.

**Integrantes:**

- Sergio Orellana, 221122.
- Ricardo Chuy, 221007.
- Rodrigo Mansilla, 22611.

**Dominio:** recuperación de información y asistencia documental sobre videojuegos.

**Usuario primario:** jugadores que requieren resolver una duda concreta sin consultar anticipadamente contenido posterior a su progreso.

Consolidamos este anteproyecto a partir del diseño y la implementación disponibles en el repositorio. Conservamos las dieciséis secciones de la plantilla y expresamos las metas como criterios de evaluación, sin presentarlas como resultados ya alcanzados. En el [informe técnico final](informe-final.md) documentamos los experimentos, las mediciones observadas y las limitaciones.

## 2. Resumen ejecutivo

Proponemos un asistente que permita consultar guías de videojuegos mediante preguntas en lenguaje natural y recibir respuestas respaldadas por fragmentos verificables. Abordamos la dispersión de información entre páginas, la dificultad de reconocer qué versión se está consultando y el riesgo de revelar soluciones o eventos posteriores al avance del jugador. Combinamos una línea base léxica con recuperación híbrida, generación estructurada, herramientas deterministas y filtros asociados al perfil. Conservamos instantáneas documentales, revisiones y metadatos para reproducir la ingesta y analizar cada respuesta. Evaluaremos recuperación, generación, operación y seguridad mediante bancos estructurados, comparaciones con la línea base y revisión de fallas; distinguiremos la cobertura de The Legend of Zelda y Ninja Gaiden (NES) de la ampliación exploratoria a otros cinco juegos.

## 3. Problema

### Situación actual

Identificamos que las guías distribuyen información relacionada entre páginas de objetos, mapas, enemigos y recorridos. Una consulta aparentemente sencilla puede requerir reconocer sinónimos, seleccionar una quest y reunir evidencia de varias secciones. Al abrir una guía completa, el jugador puede encontrar simultáneamente información necesaria y contenido que todavía no desea conocer.

### Dolor o limitación

Buscamos reducir el esfuerzo de localizar evidencia pertinente sin delegar la respuesta a conocimiento no verificable del modelo. Consideramos especialmente problemáticas las respuestas que mezclan juegos, atribuyen una solución a una versión incorrecta o citan una página que no respalda la afirmación. El acceso a una wiki pública no implica que todo su contenido sea apropiado para el progreso seleccionado.

### Impacto

Reconocemos como costos el tiempo dedicado a comprobar instrucciones incorrectas, la interrupción de la experiencia de juego y la exposición irreversible a spoilers. En este dominio no tratamos decisiones médicas, jurídicas o financieras; evaluamos la confianza documental y el respeto de preferencias del usuario dentro de un entorno académico de demostración.

### Pregunta principal del sistema

Formulamos la tarea del sistema de la siguiente manera: ¿qué respuesta podemos ofrecer a la pregunta del jugador utilizando exclusivamente evidencia del juego activo y compatible con su perfil, y qué fuentes permiten verificarla?

## 4. Usuario y contexto

| Usuario | Necesidad | Permisos | Riesgo de error |
| --- | --- | --- | --- |
| Jugador con progreso limitado | Resolver una duda del tramo alcanzado | Evidencia del juego y progreso registrados | Revelar soluciones, eventos o ubicaciones posteriores |
| Jugador que acepta spoilers | Consultar el corpus completo del juego | Perfil `completionist` sin restricción de progreso | Recibir una respuesta incorrecta o mezclar versiones |
| Administrador de demostración | Revisar trazas y configuración | Acceso local a auditoría y operaciones administrativas | Exposición de datos en logs o modificación no intencional |
| Equipo evaluador | Reproducir y explicar decisiones | Bancos, snapshots, código y artefactos | Confundir una prueba parcial con una garantía general |

Utilizamos perfiles sembrados y seleccionables por identificador. No incorporamos autenticación real; por ello delimitamos los permisos como un mecanismo demostrativo que deberá vincularse a una identidad verificada antes de un despliegue público.

## 5. Objetivos

### Objetivo general

Diseñar e implementar un sistema de recuperación y generación fundamentada que responda consultas documentales sobre videojuegos con evidencia trazable, controles de acceso por progreso y evaluación reproducible.

### Objetivos específicos

1. Construir una ingesta determinista que conserve texto, fuente, sección, identificador, revisión y metadatos de acceso.
2. Comparar una línea base BM25 con recuperación híbrida y justificar las decisiones de segmentación, representación y fusión.
3. Producir respuestas validadas con citas, abstención, identificación de herramientas y escalamiento por incertidumbre.
4. Integrar un flujo de decisión que distinga preguntas documentales, consultas deterministas de progreso y acciones que no deben ejecutarse automáticamente.
5. Medir recuperación, fidelidad, cobertura, abstención, latencia, llamadas, costo y comportamiento adversario con denominadores explícitos.
6. Documentar fallas, límites de cobertura y uso de herramientas de inteligencia artificial.

## 6. Alcance

### Incluye

Incluimos snapshots textuales de wikis, consultas principalmente en inglés, ingesta fija y estructural, búsqueda léxica y semántica, generación extractiva y mediante un proveedor LLM, API, interfaz Gradio, perfiles de progreso y auditoría local. Configuramos siete juegos: `zelda1`, `ninja_gaiden_nes`, `oot`, `ac2`, `doom`, `gta_sa` y `rdr1`.

Concentramos la evaluación principal y la curaduría inicial en The Legend of Zelda y Ninja Gaiden (NES). La ampliación del corpus permite estudiar cobertura adicional, pero requiere informar su validación por separado.

### No incluye

Excluimos automatizar la partida, escribir en el estado del videojuego, ofrecer autenticación de producción, garantizar detección universal de spoilers o afirmar soporte multilingüe equivalente. No incorporamos manuales comerciales en el corpus distribuido. Las solicitudes de modificar progreso o privilegios se derivan a revisión y no se ejecutan.

### MVP

Definimos el MVP como una consulta sobre un juego con evidencia recuperada desde un snapshot, una respuesta conforme al contrato, una cita verificable y una regla activa de abstención o bloqueo. Incorporamos la búsqueda híbrida y el grafo como mejoras que deben justificar su costo frente a esa referencia.

## 7. Fuentes y gobernanza

| Fuente | Formato | Propietario o atribución | Actualización | Permiso declarado | Sensibilidad |
| --- | --- | --- | --- | --- | --- |
| StrategyWiki | Wikitext y manifiesto JSON | Colaboradores de cada página | Snapshot versionado; actualización manual | CC BY-SA 4.0 según registro de la API | Pública |
| Wikipedia | Wikitext y manifiesto JSON | Colaboradores de cada artículo | Snapshot y revisión por página | CC BY-SA 4.0 según configuración | Pública |
| Grand Theft Wiki | Wikitext y manifiesto JSON | Colaboradores del sitio | Snapshot versionado | CC BY-SA 3.0 declarada | Pública |
| Wikis especializadas de Fandom | Wikitext y manifiesto JSON | Colaboradores de cada wiki | Snapshot versionado | CC BY-SA declarada; conservar la información de versión disponible | Pública |
| Zeldapedia y Zelda Wiki | Wikitext y manifiesto JSON | Colaboradores de cada wiki | Snapshot versionado | GFDL / GFDL 1.3 declarada; carpetas y atribución separadas | Pública |

Conservamos URL, título y `revid` en los manifiestos. Asociamos a cada fragmento un hash del texto, el origen y la ubicación del contenido. Antes de redistribuir derivados debemos preservar atribución y condiciones de la fuente correspondiente; no asignamos una licencia uniforme a toda la colección.

Tratamos las fuentes adicionales sin clasificación suficiente de manera restrictiva para perfiles limitados; una sección general puede autorizarse mediante reglas explícitas del juego. Conservamos separadas las fuentes que abarcan una franquicia y las excluimos por defecto de la recuperación secundaria. Un cambio de revisión o metadatos debe invalidar la representación persistida, incluso si el texto visible permanece igual.

## 8. Requisitos

### Funcionales

1. Validar pregunta, juego y perfil; rechazar entradas fuera del contrato.
2. Recuperar documentos del juego activo y aplicar permisos antes de generar.
3. Responder con evidencia suficiente o abstenernos explícitamente.
4. Conservar el contrato `Answer`, con citas, estado de abstención, herramienta y revisión humana.
5. Mostrar en la interfaz la evidencia exacta de la respuesta, incluida su revisión.
6. Registrar decisiones, contexto autorizado, respuesta final y degradaciones.
7. Rechazar acciones críticas sin modificar perfiles ni privilegios.

### No funcionales

1. Reproducir dependencias con `uv.lock`, snapshots versionados y comandos de ingesta.
2. Medir latencia media y P95, tokens, invocaciones y costo según configuración declarada.
3. Restringir las llamadas a herramientas, los reintentos y los presupuestos del proveedor.
4. Sanitizar datos sensibles en consultas y auditoría, con retención configurable.
5. Mantener una alternativa extractiva para operar sin generación remota, identificando la degradación cuando corresponda.

## 9. Arquitectura

En la ruta documental adoptamos el flujo `entrada → validación → router → recuperación → acceso → evidencia → generación → validación → respuesta y auditoría`. Las herramientas construyen una respuesta determinista a partir de resultados autorizados y pasan a validación de salida sin utilizar el generador. En la ingesta recorremos `fuentes → extracción → limpieza → secciones → chunks → metadatos → índices`. Presentamos ambos diagramas formales en [arquitectura](../architecture/overview.md).

| Componente | Función | Entrada | Salida | Justificación |
| --- | --- | --- | --- | --- |
| Ingesta | Normalizar y segmentar | Snapshot y manifiesto | Chunks versionados | Reproducibilidad documental |
| Recuperador | Encontrar evidencia | Pregunta y juego | Candidatos ordenados | Complementar coincidencia exacta y similitud |
| Filtros de acceso | Autorizar contenido | Candidato y perfil | Evidencia permitida | Respetar juego y progreso |
| Router y herramientas | Resolver solicitudes estructuradas | Intención y parámetros | Datos deterministas o revisión | Evitar reconstruir desde texto el progreso personal |
| Generador | Redactar o extraer | Pregunta y evidencia | `Answer` | Fundamentación y formato verificable |
| Guardrails de salida | Verificar respuesta | Respuesta y contexto | Aceptación o abstención | Rechazar citas y estructuras inválidas |
| API y Gradio | Exponer el sistema | Solicitud validada | Respuesta, evidencia y explicación | Integrar la demostración |
| Auditoría | Preservar decisiones | Traza sanitizada | Registro SQLite | Diagnóstico y evaluación |

En el perfil `full` representamos el procesamiento mediante un grafo de estado con reintentos acotados. No asumimos que disponer de un grafo implique autonomía abierta: las transiciones y las herramientas permitidas quedan determinadas por reglas explícitas.

## 10. Recuperación y RAG

- **Chunking:** conservamos ventanas fijas como línea base y segmentación estructural por encabezados para el servicio. Utilizamos un máximo habitual de 225 palabras y un solapamiento de 30 en la variante fija; la segmentación estructural empaqueta líneas completas, divide por palabras las que superan el máximo y agrupa secciones pequeñas.
- **Metadatos:** preservamos `text`, `source`, `page`, `chunk_id`, `version`, URL, sección, hash, juego, origen y restricciones. En wikis interpretamos `page` como ordinal de sección.
- **Embeddings:** seleccionamos `intfloat/multilingual-e5-small`, de 384 dimensiones, con prefijos de consulta y pasaje.
- **Índice:** persistimos vectores y metadatos en Chroma y conservamos un índice léxico BM25.
- **Búsqueda:** fusionamos rankings mediante RRF con constante 60; conservamos variantes de consulta con corrección ortográfica y glosario.
- **Reranking:** mantenemos la comparación experimental; no activamos un cross-encoder por defecto al no haber demostrado una mejora suficiente en los bancos utilizados.
- **Citas:** verificamos el triple fuente, ordinal de sección e identificador contra la evidencia autorizada y preservamos la revisión documental.
- **Abstención:** evaluamos suficiencia documental; no interpretamos un score alto como garantía de respuesta. El flujo con LLM admite revisión de evidencia y recuperación adicional bajo un límite.

La familia E5 se documenta en [Wang et al. (2024)](https://arxiv.org/abs/2402.05672) y su configuración concreta en la [ficha del modelo](https://huggingface.co/intfloat/multilingual-e5-small). Utilizamos la fusión de posiciones descrita por [Cormack, Clarke y Büttcher (2009)](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf).

## 11. Herramientas y agentes

| Herramienta o ruta | Propósito | Parámetros | Permisos | Validación |
| --- | --- | --- | --- | --- |
| `query_game_facts` | Enumerar hechos estructurados de jefes de Zelda | Quest y nivel | Solo lectura y filas autorizadas | Rangos, consulta parametrizada, límite y citas |
| `next_available_levels` | Consultar niveles registrados y pendientes | Perfil y juego | Lectura del perfil seleccionado | Modelo de progreso y configuración |
| `update_progress` | Detectar una solicitud de cambio | Texto y progreso mencionado | Sin ejecución automática | `needs_human_review`; estado intacto |
| `critical_action` | Detectar borrado, cambio de rol o desbloqueo | Intención | Sin ejecución automática | Rechazo o revisión |
| Ruta documental | Responder preguntas informativas | Pregunta y contexto | Evidencia autorizada | Contrato, citas y abstención |

Justificamos la herramienta de hechos porque una enumeración puede abarcar más información que el contexto documental limitado. La consulta de progreso depende del perfil, no de una wiki. Los niveles pendientes no constituyen un planificador de prerrequisitos jugables.

## 12. Evaluación

### Banco de pruebas

Contamos con un banco principal histórico de 54 casos: 39 de Zelda y 15 de Ninja Gaiden. Su distribución incluye 8 directos, 5 paráfrasis, 5 identificadores exactos, 4 compuestos, 2 ambiguos, 4 etiquetados como no respondibles, 3 de variante y 23 de robustez; un caso adicional de robustez también exige abstención. Conservamos bancos difíciles, de fuentes adicionales, de herramientas y de seguridad.

Evaluaremos por separado las revisiones documentales reales o controladas. Las diferencias entre quests o nombres regionales no sustituyen una prueba de actualización de documentos. Cada caso debe conservar los campos obligatorios del curso y la evidencia esperada que permita repetir su evaluación.

### Métricas

Las siguientes metas son decisiones del proyecto, no umbrales universales impuestos por el curso.

| Métrica | Definición | Meta del proyecto | Método |
| --- | --- | --- | --- |
| Hit rate@5, denominado históricamente Recall@5 | Proporción de consultas con alguna evidencia relevante en cinco posiciones | ≥ 0.80 | Casos respondibles y denominador explícito |
| Recall de evidencia@k | Partes esperadas recuperadas entre todas las partes esperadas | Comparar con la línea base | `coverage@k`; no equivale al recall de todos los documentos del corpus |
| MRR | Recíproco del primer rango relevante | Mejorar la línea base | Promedio sobre el mismo banco |
| Precisión de citas | Citas relevantes entre citas emitidas | ≥ 0.90 | Relevancia frente a la evidencia esperada; identidad y apoyo factual se verifican por separado |
| Fidelidad | Afirmaciones respaldadas por contexto final | Revisar errores y desacuerdos | Juez con contexto más muestra humana |
| Abstención | Corrección global y sensibilidad en no respondibles | ≥ 0.90 en cada indicador, informando denominadores | Matriz de confusión; sensibilidad no evaluable si no hay casos no respondibles |
| Latencia P95 | Percentil 95 por consulta | < 6 s en configuración declarada | Corrida identificada y modo de caché |
| Seguridad | Ataques y fugas observados | Cero fugas en la suite definida | Oráculo independiente y casos adversarios |

## 13. Seguridad

Aplicamos validación estructural, detección de patrones de inyección, delimitación del contexto y cuarentena de contenido sospechoso. Comprobamos juego, progreso y procedencia antes de entregar evidencia; el contenido general requiere atención porque puede contener soluciones posteriores aunque su título no identifique una ubicación.

Redactamos correos, teléfonos y secretos detectables antes de persistir trazas. Limitamos solicitudes y herramientas, utilizamos SQL de lectura y mantenemos sin ejecución las acciones críticas. Validamos salidas y citas contra el contexto autorizado; preservamos la distinción entre integridad de cita y fidelidad semántica.

Probamos intentos directos e indirectos, evasión de permisos, afirmaciones forzadas y degradación. No interpretamos un resultado favorable en una suite finita como demostración de ausencia absoluta de ataques o spoilers.

## 14. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación | Prueba |
| --- | --- | --- | --- | --- |
| Spoiler en páginas agregadas | Alta | Alto | Clasificación conservadora y evidencia restringida | Casos de entidades y narrativa independientes del gate |
| Recuperación insuficiente | Media | Alto | Híbrida, expansión y abstención | Recall, MRR y diagnóstico por caso |
| Cita válida con afirmación no respaldada | Media | Alto | Evaluación contra contexto final | Revisión de fidelidad |
| Fuente o revisión obsoleta | Media | Medio | Manifiestos e invalidación de índices | Reingesta con cambio de revisión |
| Indisponibilidad del proveedor | Media | Medio | Presupuesto, caché y degradación explícita | Excepción y timeout inyectados |
| Sobreajuste del router | Alta | Medio | Conservar fallas y conjunto nuevo no inspeccionado | Evaluación antes de corregir |
| Confundir perfil local con identidad | Alta fuera de demo | Alto | Restringir alcance académico | Pruebas de rutas administrativas |
| Atribución o licencia incompleta | Media | Alto | Separación por fuente y manifiestos | Inspección previa a redistribución |

## 15. Plan de trabajo

No atribuimos responsabilidades individuales ni fechas retrospectivas que no estén documentadas. Organizamos la responsabilidad de forma colectiva y vinculamos los hitos a entregables verificables.

| Fase | Actividad | Responsable | Entregable | Fecha o condición |
| --- | --- | --- | --- | --- |
| Línea base | Ingesta fija, BM25 y banco inicial | Equipo del proyecto | Código y métricas de referencia | Evidencia histórica en el repositorio |
| RAG | Segmentación estructural, E5, RRF y generación | Equipo del proyecto | Pipeline y comparación | Configuración y banco identificados |
| Herramientas | Router, hechos y progreso | Equipo del proyecto | Contratos y pruebas | Validación de casos nominales y adversarios |
| Evaluación | Métricas, revisión de versiones y fidelidad | Equipo del proyecto | Artefactos comparativos | Antes de declarar cierre |
| Seguridad | Ataques, permisos y clasificación de spoilers | Equipo del proyecto | Reporte y fallas reproducibles | Sobre la integración final |
| Documentación | Anteproyecto e informe final | Equipo del proyecto | Dos documentos consistentes | Comprobar maquetación final |
| Defensa | Preparación individual y ensayo | Equipo del proyecto | Demo de 15 minutos | Registrar cuando se realice |

## 16. Referencias

- Lewis, P., et al. (2020). [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401).
- Cormack, G. V., Clarke, C. L. A., y Büttcher, S. (2009). [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf).
- Wang, L., et al. (2024). [Multilingual E5 Text Embeddings: A Technical Report](https://arxiv.org/abs/2402.05672).
- Intfloat. [Ficha de multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).
- LangChain. [Documentación de LangGraph](https://docs.langchain.com/oss/python/langgraph/overview).
- Pydantic. [Modelos y validación](https://pydantic.dev/docs/validation/latest/concepts/models/).
- Equipo del proyecto. [Manifiestos y atribución del corpus](../../data/wiki_snapshot/README.md), [configuración de fuentes](../../config/sources.yaml) y [decisiones de arquitectura](../architecture/decisions/README.md).
- Universidad del Valle de Guatemala. [Instrucciones del proyecto final](instructions.md) y [presentación de CC3103](presentation.md).

Registramos el apoyo de Codex y subagentes en la auditoría del repositorio, los ajustes de implementación y la redacción de estos documentos. Conservamos esta declaración sin atribuir revisiones humanas o un historial completo de asistencia anterior que no podamos verificar; ampliamos el alcance conocido de uso de IA en el informe final.
