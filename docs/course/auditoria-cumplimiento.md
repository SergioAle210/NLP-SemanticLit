# Matriz de requisitos y evidencias

Contrastamos las [instrucciones](instructions.md) y la [presentación del curso](presentation.md) con la implementación y sus artefactos. Diferenciamos evidencia disponible de una garantía general o una actividad humana todavía no acreditada. Los documentos oficiales se conservan sin modificar.

| Requisito | Evidencia | Alcance de cumplimiento |
| --- | --- | --- |
| Problema, usuario y costo de error (§5.1) | [Alcance](../overview/problem-and-scope.md), informe final §2–3 | Definidos para asistencia documental y spoilers |
| Fuentes y autorización (§5.2) | [Fuentes](../data/sources.md), manifiestos y configuración | Atribución y licencias declaradas; conservar condiciones por fuente |
| Extracción, limpieza y chunking (§5.3) | [Ingesta](../ingestion/README.md), código y pruebas | Pipeline reproducible desde snapshots |
| Cinco metadatos obligatorios (§5.3) | [Modelo de chunk](../ingestion/metadata.md) | `page` documentado como ordinal de sección; revisión separada de quest |
| Recuperación justificada (§5.4) | [Recuperación](../retrieval/README.md), ADRs y experimentos | BM25/E5/RRF comparados; alternativas descartadas conservadas |
| Generación fundamentada (§5.5) | [Contrato](../contracts/generation.md), artefactos históricos y nuevos | Citas y abstención implementadas; fidelidad completa no certificada |
| Herramienta o decisión funcional (§5.6) | [Herramientas](../tools/README.md), router y tests | SQL de lectura, progreso y derivación de acciones |
| Dos flujos arquitectónicos (§6) | [Diagramas](../architecture/overview.md), informe final §6 | Usuario e ingesta, decisiones, estado, errores y controles |
| Banco mínimo y categorías (§8) | [Banco](../evaluation/test-bank.md), `eval/cases.jsonl` | Principal histórico de 54 casos; categorías y denominadores declarados |
| Revisión documental (§8) | [Evaluación sintética con E5](../../eval/results/20261116T022250583253Z-b13d858d_versions_synthetic-document-revisions.json) y pruebas de índice | 2/2; no se equipara quest con revisión ni se afirma selección temporal en API. La configuración declarada por el ensayo no representa todos sus componentes efectivos |
| Herramientas nominal/error/rango/confirmación/degradación (§8) | Bancos tools y heldout, tests | Acciones críticas no ejecutadas; aprobación persistente fuera de alcance |
| Recuperación cuantitativa (§9) | [Métricas](../evaluation/metrics.md), scorecards | Recall por unidades de evidencia en `coverage@k`, MRR y ruido; separado del hit rate histórico y del recall documental |
| Generación cuantitativa y cualitativa (§9) | Métricas, juez con contexto y análisis de fallas | Indicadores léxicos y análisis cualitativo disponibles; nuevo juez sin medición real. El curso no exige específicamente revisión humana completa |
| Operación (§9) | Trazas y artefactos esquema 2 | Latencia, llamadas, caché, tokens, estimación de costo y degradaciones |
| Inyección, permisos y acciones críticas (§10) | [Suite del cierre previo](../../eval/results/20261116T022654688800Z-b171d853_security_guarded.json), [reporte](../security/report.md) | 37/42 en esa corrida; cinco fallas de abstención extractiva. Perfiles locales, sin autenticación de producción |
| Spoilers indirectos | Política curada, oráculos v1/v2 y [pruebas de contenido](../../tests/test_content_policy.py) | El cierre previo registró contenido 7/9 y quests 2/2. Después reforzamos celdas y rutas de Hyrule. La revisión ampliada reprodujo fugas en Ocarina of Time |
| Salida validada (§11) | `Answer`, `Source` y tests | Campos obligatorios conservados; evidencia añadida al contenedor HTTP |
| Cadena auditable (diapositiva 16) | [Traza](../contracts/pipeline.md) | Contexto y respuesta finales, etapas y sanitización en consultas completadas; una excepción del recuperador impide persistir la traza. El JSON E2E omite parte de sus decisiones |
| Código y reproducibilidad (§12) | README, lockfile, bootstrap, Docker y scripts | Arranque limpio verificado: siete juegos, primario y adicional; preset full/BM25/offline sin llamadas remotas |
| Pruebas de integración | [XML de esta revisión](../../eval/results/2026-11-17_pytest-audit.xml), [XML del cierre previo](../../eval/results/2026-11-16_pytest-closure.xml) y [HTTP previo](../../eval/results/2026-11-16_http-closure-offline.json) | Esta revisión: 520 pruebas aprobadas, sin omisiones. Los artefactos anteriores conservan 489 pruebas y 36/36 HTTP; las siete comprobaciones HTTP de mapas se observaron en consola |
| Interfaz y evidencia visible | [Gradio](../ui/README.md) | Consulta, citas, herramienta, búsqueda y scorecard inspeccionados; contraste oscuro corregido; sin recorrido completo de teclado acreditado |
| Informe técnico (§12) | [Fuente](informe-final.md), [PDF](../../output/pdf/informe-final.pdf) y [manifiesto](../../output/pdf/informe-final.layout.json) | 15 páginas A4, incluida la carátula, y dos figuras; hash de fuente coincidente con la exportación final |
| Anteproyecto solicitado | [Anteproyecto](informe.md) y [PDF](../../output/pdf/anteproyecto.pdf) | Dieciséis secciones según la plantilla de Word, sin carátula; integrantes y carnets preservados |
| Demo y defensa individual (§12–13) | [Guion](defensa.md), [presentación del equipo](presentacion-equipo.pdf) y [video](https://youtu.be/ZC5XwdeHOQ4) | Materiales y enlace proporcionados por el equipo; su incorporación no acredita el ensayo ni el dominio individual |
| Integridad y uso de IA (§15) | Informe final §14 | Intervención conocida declarada; sin inventar historia ni revisiones |

## Lectura de cierre

**No acreditamos cumplimiento total.** Los componentes, contratos, bancos, diagramas e informe están disponibles, pero la corrida base conservada falló en los cinco casos no respondibles del banco principal y los tres del difícil. El curso exige abstenerse ante evidencia insuficiente (§5.5); esa evaluación incumple el requisito independientemente de nuestra meta numérica de 0.90. La revisión ampliada confirmó además exposición de contenido posterior en Ocarina of Time y pérdida de auditoría ante una falla de recuperación. No ejecutamos un nuevo benchmark completo después del refuerzo de mapas. La demostración formal y la defensa técnica individual también requieren participación del equipo.

Distinguimos obligaciones del curso de métodos o metas propios. Debemos evaluar fidelidad y otras dimensiones de respuesta, pero no se nos impone un juez LLM, doble anotación ni una validación humana completa del juez. Tampoco se exigen todos los recuperadores, autenticación de producción o un circuito de edición de progreso. La declaración de herramientas generativas y grado de intervención está incluida; el registro retrospectivo exhaustivo por persona y fecha es una limitación de documentación, no un formato adicional exigido por el curso.

La existencia de los entregables no implica alcanzar todas las metas de calidad. Los históricos muestran precisión de citas inferior a 0.90 y P95 superior a seis segundos en algunos bancos. La corrida base del cierre previo verifica su configuración sin proveedor remoto, pero no reemplaza una evaluación del código posterior ni una nueva corrida `full`.

La corrida base conservada obtiene hit rate@5 de 0.9388 y precisión de citas de 0.3061 en el banco principal. Conservamos la pérdida de un acierto frente a la corrida intermedia tras corregir metadatos. Su sensibilidad de abstención es cero en los bancos principal y difícil; el oráculo registra dos fallas de utilidad narrativa. El ensayo de cuarentena con extractivo mide exposición de texto de prueba, no obediencia de un modelo generativo.

La revisión posterior corrigió la exposición de rutas a mazmorras no autorizadas en los mapas de Hyrule. Proyectamos celdas completas y dependencias configuradas, conservando información útil de White Sword. Verificamos esa corrección con pruebas automatizadas y siete comprobaciones HTTP en consola; no la presentamos como una nueva ejecución de los bancos históricos.

La revisión humana de fidelidad, el ensayo de defensa y la confirmación del grado de intervención histórica de IA solo pueden acreditarse con registros del equipo. El código, los informes y el guion pueden entregarse con estas limitaciones explícitas, sin presentarlas como actividades completadas.

## Revisión ampliada del estado actual

Revisamos el código después de los commits documentales `9b606d9` y `b6a9dba`. La suite completa produjo 520 pruebas aprobadas, cero errores, cero fallas y cero omisiones en 32.659 segundos; Ruff no encontró errores. Utilizamos modelos semánticos ya descargados y desactivamos las descargas. La ejecución satisfactoria utilizó un directorio temporal nuevo dentro del proyecto y permisos para el bucle de red local requerido por las pruebas HTTP. Los intentos previos bloqueados por el entorno no se contabilizan como pruebas aprobadas.

Verificamos los hashes del banco, la evidencia y las citas de las 136 respuestas E2E conservadas, sin presentarlas como respuestas nuevas. Las dos pruebas de revisión documental conservan respuestas y citas coherentes con cada revisión. El PDF final tiene 15 páginas, incluida la carátula, y dos figuras; el anteproyecto tiene 11 páginas, sin carátula, y sus dieciséis apartados coinciden con la plantilla. La presentación del equipo tiene veinte diapositivas. Comprobamos la incorporación del enlace al video, pero no acreditamos su reproducción ni una defensa realizada.

### Hallazgos funcionales reproducidos

| Prioridad | Hallazgo y evidencia | Relación con el curso |
| --- | --- | --- |
| Alta | Con el perfil inicial de Ocarina of Time, `How do I defeat Phantom Ganon?` expone tácticas desde `oot:enemies:031`; `How does Z-targeting work?` incorpora tácticas de Twinrova desde `oot:enemies:049`. Las páginas agregadas carecen de restricciones suficientes por encabezado. Las escenas del pozo y la revelación de Saria también pasan el filtro antes de cumplir su condición narrativa. | Permisos y protección de contenido, §5.8 y §10. La fuga aparece en la evidencia final, antes de la generación |
| Alta | El [generador extractivo](../../src/gamerag/generation/base.py) responde siempre que recibe contexto, aunque este no contenga el dato solicitado. Reprodujimos el problema con preguntas nuevas sobre una garantía o una puerta y un pasaje que solo describe el combustible de una lámpara. | Abstención ante evidencia insuficiente, §5.5; afecta al modo base y al respaldo del generador remoto |
| Media | Una excepción sintética del recuperador se propaga desde el [pipeline](../../src/gamerag/pipeline.py) y evita que el [endpoint](../../src/gamerag/api.py) registre la traza. La invocación síncrona del endpoint con SQLite en memoria dejó cero trazas persistidas. | Manejo de fallas y auditoría por consulta, diapositiva 16. Esta reproducción no acredita un código HTTP observado |
| Media | El [evaluador de evidencia](../../src/gamerag/agents/evidence.py) devuelve suficiencia cuando falla su proveedor. El control de identidad de citas acepta una afirmación contradictoria si utiliza una referencia válida. | Fidelidad y tratamiento explícito de incertidumbre, §5.5. La contradicción se simuló con un generador de prueba; no es una alucinación nueva observada del proveedor |
| Media | El [resultado E2E](../../src/gamerag/evaluation/e2e.py) conserva evidencia y respuesta, pero omite candidatos, controles de entrada/salida, razón del router y detalle de herramienta. La persistencia completa requiere solicitar SQLite y que la consulta termine normalmente. | Cadena pregunta, intención, filtros, candidatos, contexto, herramienta, respuesta y citas, diapositiva 16 |
| Media | El [ensayo de revisiones](../../src/gamerag/evaluation/versions.py) construye un pipeline con un resultado y sin router ni expansión, mientras los metadatos generales declaran cinco resultados y esas funciones activas. Las respuestas 2/2 siguen siendo válidas, pero la configuración declarada necesita reconciliarse con la ejecución. | Reproducibilidad y configuración efectiva, §5.3 y §12 |
| Baja, función opcional | Una nota derivada de una revisión antigua sigue autorizada cuando cambia la revisión del mismo identificador fuente. El [control de procedencia](../../src/gamerag/guardrails/provenance.py) comprueba identidad y permisos actuales, sin contrastar la revisión original de cada dependencia. | Vigencia documental. La memoria de notas está desactivada en el perfil servido por defecto |

Las correcciones de Ocarina of Time deben conservar los controles positivos: Kokiri Sword y las instrucciones iniciales están permitidos desde el primer nivel; las tácticas del Forest Temple deben habilitarse al alcanzar esa mazmorra, y su desenlace al completarla. Bloquear indiscriminadamente páginas de objetos o enemigos impediría consultas legítimas. La pregunta inocua sobre selección de objetivos muestra que no basta con prohibir términos en la entrada.

Para cerrar el defecto de abstención necesitamos evaluar suficiencia documental sobre familias nuevas de preguntas respondibles y no respondibles, incluidas paráfrasis y respuestas al final del pasaje. Un corte por score, reglas ajustadas exclusivamente a los ocho casos fallidos o abstenerse siempre no demostrarían una solución general. Debemos distinguir falta de evidencia, fallo del evaluador y fallo operativo.

### Alcance de las métricas y de la entrega

Los valores de Precision@5 y recall de unidades de evidencia incluidos en el informe se obtuvieron mediante recuentos sobre resultados conservados. La utilidad `evaluation.retrieval` calcula `coverage@k`; los resúmenes E2E y el scorecard no generan automáticamente ambas medidas sobre los primeros cinco resultados. La cobertura del contexto completo no debe sustituirlas cuando el contexto contiene más de cinco fragmentos.

Esta revisión termina con un dictamen y reproducciones concretas; no presenta estos hallazgos como correcciones implementadas. No realizamos nuevas llamadas al modelo remoto, un nuevo benchmark completo, un arranque Docker adicional ni una nueva inspección de la interfaz. Los ensayos anteriores conservan su alcance histórico. La autenticación de producción, la edición de progreso y las pistas escalonadas no se convierten en requisitos nuevos del curso.

## Anexo: explicación del proyecto y cambios por archivo

### Qué estamos construyendo

Construimos GameRAG, un asistente que responde preguntas sobre videojuegos utilizando guías documentales y el progreso registrado del jugador. Buscamos que cada respuesta pueda comprobarse mediante una cita y que la evidencia entregada no revele soluciones o escenas posteriores al acceso permitido. Disponemos de siete juegos; la curaduría y evaluación más extensa corresponden a The Legend of Zelda y Ninja Gaiden.

El flujo principal consta de seis pasos:

1. Preparamos snapshots de las fuentes, limpiamos el texto y lo dividimos en fragmentos con fuente, sección, revisión y metadatos de acceso.
2. Recuperamos candidatos con BM25 y embeddings E5; combinamos sus rankings y aplicamos la configuración de búsqueda elegida.
3. Filtramos por juego, quest, progreso, cuarentena y contenido. Cuando solo una parte está autorizada, conservamos esa parte con su referencia original.
4. Generamos una respuesta con Haiku o presentamos extractos. Validamos la estructura y las citas; registramos errores y degradaciones.
5. Para determinadas consultas utilizamos herramientas de lectura, como la tabla de jefes o el perfil de progreso. Las solicitudes de modificación se derivan a revisión; no implementamos su aprobación y ejecución desde la interfaz.
6. Entregamos respuesta y evidencia exacta mediante FastAPI y Gradio, guardamos una traza sanitizada y evaluamos recuperación, generación, seguridad y operación.

Reutilizamos modelos preentrenados. Nuestro trabajo se concentra en preparar las fuentes, recuperar evidencia, aplicar permisos, integrar herramientas y comprobar el comportamiento del sistema. La autenticación real, la edición de progreso y las pistas graduadas permanecen fuera de este cierre.

### Qué mejoramos durante el cierre

La aplicación ya contaba con recuperación híbrida, generación y herramientas. Corregimos problemas de configuración, clasificación de quests, spoilers en páginas generales y evidencia de herramientas; después ampliamos la protección a celdas de mapa y rutas dependientes de Hyrule. También reforzamos la validación de citas, la invalidación de índices, el aislamiento de solicitudes concurrentes y la conservación del contexto realmente utilizado.

Implementamos los evaluadores y completamos la documentación académica, manteniendo visibles los resultados desfavorables y las limitaciones de trazabilidad descritas en esta revisión. La suite de 520 pruebas valida comportamientos concretos; no implica que todas las respuestas sean correctas ni reemplaza los benchmarks de calidad. Conservamos tanto su nuevo XML como el anterior de 489 pruebas, cada uno con su alcance original.

El inventario siguiente explica las rutas afectadas por la auditoría y los cambios relacionados que integramos en esta entrega. No lo usamos como contador del estado transitorio de Git: la clasificación entre archivos modificados y sin seguimiento cambia al preparar los commits. Los resultados contienen evidencia experimental; no todos los archivos son código nuevo. La plantilla de anteproyecto ya existía y la completamos.

### Configuración y ejecución

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [.dockerignore](../../.dockerignore) | Excluimos temporales y exportaciones del contexto Docker; conservamos el scorecard que consulta la interfaz. |
| [.env.example](../../.env.example) | Comentamos los overrides que anulaban full y corregimos la referencia a Gradio. |
| [.gitignore](../../.gitignore) | Excluimos los temporales de maquetación y verificación para que no aparezcan como cambios del repositorio. |
| [Dockerfile](../../Dockerfile) | Corregimos los comentarios sobre Gradio y las licencias por fuente; las instrucciones de construcción se mantienen. |
| [compose.yaml](../../compose.yaml) | Corregimos el puerto documentado de la interfaz a 7860; no cambiamos la definición de los servicios. |
| [pyproject.toml](../../pyproject.toml) | Actualizamos la descripción del paquete al alcance de siete videojuegos; no añadimos dependencias. |
| [config/games/zelda1.yaml](../../config/games/zelda1.yaml) | Añadimos clasificación de quests y reglas para Silver Arrows, tesoros, jefes, recorridos y dependencias entre celdas de los mapas de Hyrule. |
| [config/games/ninja_gaiden_nes.yaml](../../config/games/ninja_gaiden_nes.yaml) | Añadimos restricciones para desenlaces narrativos según la etapa alcanzada. |
| [scripts/docker-entrypoint.sh](../../scripts/docker-entrypoint.sh) | Preparamos con bootstrap los corpus que necesita la configuración antes de iniciar la API. |
| [scripts/render_report.py](../../scripts/render_report.py) | Creamos la exportación del informe a PDF con tablas, diagramas, conteo de páginas y hashes verificables. |
| [scripts/verify_running_api.py](../../scripts/verify_running_api.py) | Creamos 36 comprobaciones HTTP de configuración, evidencia, citas y seguridad; exigimos modo LLM sin conexión. |

### Aplicación y seguridad

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [src/gamerag/bootstrap.py](../../src/gamerag/bootstrap.py) | Creamos el preparador compartido de corpus primario y secundario, con invalidación por cambios y publicación atómica. |
| [src/gamerag/settings.py](../../src/gamerag/settings.py) | Normalizamos claves vacías o con espacios como ausencia de credenciales. |
| [src/gamerag/games.py](../../src/gamerag/games.py) | Definimos y validamos reglas por pasaje, etapa, nivel y celda de mapa dentro de la configuración de cada juego. |
| [src/gamerag/ingest/location.py](../../src/gamerag/ingest/location.py) | Clasificamos quests a partir de títulos y encabezados descendientes, evitando mezclar recorridos. |
| [src/gamerag/ingest/models.py](../../src/gamerag/ingest/models.py) | Añadimos is_excerpt y source_hash para distinguir el extracto permitido del fragmento original. |
| [src/gamerag/guardrails/content.py](../../src/gamerag/guardrails/content.py) | Creamos la proyección por secciones, pasajes, filas y celdas completas de mapa; filtramos rutas y bordes no verificables conservando las citas. |
| [src/gamerag/guardrails/base.py](../../src/gamerag/guardrails/base.py) | Validamos el triple chunk_id, fuente y página, además del juego del contexto. |
| [src/gamerag/guardrails/injection.py](../../src/gamerag/guardrails/injection.py) | Detectamos instrucciones dirigidas al modelo en documentos y evitamos reutilizar una decisión de cuarentena si cambia el texto. |
| [src/gamerag/guardrails/provenance.py](../../src/gamerag/guardrails/provenance.py) | Exigimos fuentes originales autorizadas para las notas; impedimos cadenas de notas que eludan las restricciones. |
| [src/gamerag/tools/router.py](../../src/gamerag/tools/router.py) | Filtramos las fuentes y filas de herramientas; devolvemos evidencia limitada a las filas permitidas y aclaramos que no editamos progreso. |
| [src/gamerag/pipeline.py](../../src/gamerag/pipeline.py) | Integramos controles de contenido, evidencia y respuesta finales, telemetría por solicitud, tiempos acumulados y comprobación del corpus secundario. |
| [src/gamerag/graph.py](../../src/gamerag/graph.py) | Conservamos el historial de intentos y el contexto final en reescrituras y búsqueda secundaria; medimos las etapas. |
| [src/gamerag/telemetry.py](../../src/gamerag/telemetry.py) | Creamos la captura de llamadas, fallos y tiempos mediante contextos separados para consultas concurrentes. |
| [src/gamerag/agents/evidence.py](../../src/gamerag/agents/evidence.py) | Registramos fallas del evaluador y la alternativa utilizada sin copiar mensajes sensibles completos al log. |
| [src/gamerag/agents/planner.py](../../src/gamerag/agents/planner.py) | Registramos el regreso a la consulta original cuando falla la planificación. |
| [src/gamerag/generation/base.py](../../src/gamerag/generation/base.py) | Aislamos el error por solicitud y registramos la degradación al generador extractivo. |
| [src/gamerag/llm.py](../../src/gamerag/llm.py) | Registramos intentos, caché, consumo y errores; controlamos reintentos y presupuesto compartido dentro de un proceso. |
| [src/gamerag/retrieval/dense.py](../../src/gamerag/retrieval/dense.py) | Invalidamos el índice al cambiar contenido, revisión o permisos y manejamos filtros sin resultados. |
| [src/gamerag/schemas.py](../../src/gamerag/schemas.py) | Añadimos EvidenceDocument con texto autorizado, revisión, hashes y marcas de redacción para auditoría. |
| [src/gamerag/store.py](../../src/gamerag/store.py) | Persistimos la traza ampliada, sanitizamos texto sensible y serializamos el acceso a SQLite bajo concurrencia. |
| [src/gamerag/api.py](../../src/gamerag/api.py) | Devolvemos evidencia exacta en /ask, páginas originales en /search y configuración efectiva sin credenciales en /health. |

### Interfaz

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [src/gamerag/ui/client.py](../../src/gamerag/ui/client.py) | Corregimos la documentación del cliente HTTP para identificar Gradio. |
| [src/gamerag/ui/components.py](../../src/gamerag/ui/components.py) | Mostramos versiones y extractos autorizados, validamos enlaces, usamos las metas del scorecard y retiramos la indicación de pistas no implementadas. |
| [src/gamerag/ui/puesto.py](../../src/gamerag/ui/puesto.py) | Usamos la evidencia de /ask sin repetir la búsqueda y mostramos la página real del modo de búsqueda directa. |
| [src/gamerag/ui/puesto.css](../../src/gamerag/ui/puesto.css) | Corregimos el contraste de los encabezados en modo oscuro. |
| [src/gamerag/ui/theme.py](../../src/gamerag/ui/theme.py) | Incluimos los ajustes visuales aportados por el usuario: distribución adaptable, anchos estables, selectores, ejemplos y colores de controles. |
| [src/gamerag/ui/tokens.json](../../src/gamerag/ui/tokens.json) | Conservamos los cambios de colores aportados por el usuario para texto sobre el escritorio y documentos en modo oscuro. |

### Evaluación

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [src/gamerag/evaluation/artifacts.py](../../src/gamerag/evaluation/artifacts.py) | Centralizamos resultados de esquema 2, hashes, configuración sin secretos, nombres únicos y telemetría por solicitud. |
| [src/gamerag/evaluation/e2e.py](../../src/gamerag/evaluation/e2e.py) | Evaluamos base o full con configuración efectiva y preservamos evidencia, respuesta, errores y consumo por consulta. |
| [src/gamerag/evaluation/compare.py](../../src/gamerag/evaluation/compare.py) | Entregamos contexto autorizado al juez y guardamos por separado correctitud, fidelidad, cobertura y soporte de citas. |
| [src/gamerag/evaluation/diagnostics.py](../../src/gamerag/evaluation/diagnostics.py) | Calculamos sobre evidencia conservada y distinguimos precisión de citas, abstención y hit rate. |
| [src/gamerag/evaluation/scorecard.py](../../src/gamerag/evaluation/scorecard.py) | Separamos metas de regresiones, detectamos comparaciones incompatibles y hacemos comprobaciones sin modificar resultados. |
| [src/gamerag/evaluation/security.py](../../src/gamerag/evaluation/security.py) | Incorporamos oráculos independientes y conservamos configuración, trazas y resultados únicos. |
| [src/gamerag/evaluation/security_report.py](../../src/gamerag/evaluation/security_report.py) | Generamos descripciones acordes con el generador utilizado y distinguimos exposición de texto de obediencia de un LLM. |
| [src/gamerag/evaluation/tools_eval.py](../../src/gamerag/evaluation/tools_eval.py) | Guardamos evidencia autorizada, errores, degradaciones y procedencia de la evaluación de herramientas. |
| [src/gamerag/evaluation/spoiler_oracle.py](../../src/gamerag/evaluation/spoiler_oracle.py) | Comprobamos contenido prohibido y permitido directamente en respuesta y evidencia, sin invocar el filtro de producción. |
| [src/gamerag/evaluation/versions.py](../../src/gamerag/evaluation/versions.py) | Reingestamos dos revisiones sintéticas y verificamos sustitución del dato, revisión de la cita e invalidación del índice. |

### Documentación

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [README.md](../../README.md) | Actualizamos alcance, instalación, bootstrap, perfiles, API, Gradio, Docker y enlaces a las comprobaciones y entregables. |
| [docs/README.md](../../docs/README.md) | Reorganizamos la navegación y distinguimos documentación vigente de notas históricas. |
| [docs/api/README.md](../../docs/api/README.md) | Documentamos endpoints, configuración efectiva, evidencia exacta, páginas, errores y alcance de las mediciones HTTP. |
| [docs/architecture/access-control.md](../../docs/architecture/access-control.md) | Explicamos filtros, quests y proyección de evidencia, con los límites de la política de contenido. |
| [docs/architecture/decisions/README.md](../../docs/architecture/decisions/README.md) | Incorporamos ADR-0014 al índice y aclaramos la lectura temporal del contexto de los ADR; conservamos las decisiones históricas. |
| [docs/architecture/decisions/0001-english-first.md](../../docs/architecture/decisions/0001-english-first.md) | Añadimos una nota de vigencia para distinguir la decisión histórica del estado actual. |
| [docs/architecture/decisions/0002-strategywiki-corpus.md](../../docs/architecture/decisions/0002-strategywiki-corpus.md) | Añadimos una nota de vigencia para distinguir el corpus inicial de las fuentes actuales. |
| [docs/architecture/decisions/0003-access-control-as-spoiler-gates.md](../../docs/architecture/decisions/0003-access-control-as-spoiler-gates.md) | Añadimos una nota de vigencia sobre los controles y límites actuales, conservando la decisión. |
| [docs/architecture/decisions/0004-sqlite-and-demo-profiles.md](../../docs/architecture/decisions/0004-sqlite-and-demo-profiles.md) | Añadimos una nota de vigencia para distinguir perfiles de demostración y autenticación. |
| [docs/architecture/decisions/0005-wikitext-cleaning.md](../../docs/architecture/decisions/0005-wikitext-cleaning.md) | Añadimos una nota de vigencia sobre el alcance actual de las reglas y las pruebas de limpieza. |
| [docs/architecture/decisions/0006-fixed-chunking-baseline.md](../../docs/architecture/decisions/0006-fixed-chunking-baseline.md) | Añadimos una nota de vigencia sobre segmentación y controles actuales, preservando el experimento inicial. |
| [docs/architecture/decisions/0007-per-game-config.md](../../docs/architecture/decisions/0007-per-game-config.md) | Añadimos una nota de vigencia para relacionar la decisión inicial con los siete juegos configurados. |
| [docs/architecture/decisions/0008-relevance-by-evidence-text.md](../../docs/architecture/decisions/0008-relevance-by-evidence-text.md) | Añadimos una nota de vigencia sobre las unidades de evidencia y la metodología actual. |
| [docs/architecture/decisions/0009-phase3-retrieval-config.md](../../docs/architecture/decisions/0009-phase3-retrieval-config.md) | Añadimos una nota de vigencia que separa la selección histórica de las evaluaciones posteriores. |
| [docs/architecture/decisions/0010-query-expansion.md](../../docs/architecture/decisions/0010-query-expansion.md) | Añadimos una nota de vigencia sobre el glosario de Ninja Gaiden y la reescritura ya implementados. |
| [docs/architecture/decisions/0011-flat-fusion-exact-dense.md](../../docs/architecture/decisions/0011-flat-fusion-exact-dense.md) | Añadimos una nota de vigencia sin sustituir los resultados históricos de fusión y búsqueda exacta. |
| [docs/architecture/decisions/0012-location-aliases-phrase-tokens.md](../../docs/architecture/decisions/0012-location-aliases-phrase-tokens.md) | Añadimos una nota de vigencia para distinguir representación de búsqueda y controles de acceso. |
| [docs/architecture/decisions/0013-intent-router-and-tools.md](../../docs/architecture/decisions/0013-intent-router-and-tools.md) | Añadimos una nota de vigencia sobre herramientas, evidencia y acciones que no se ejecutan. |
| [docs/architecture/decisions/0014-serving-profile-and-secondary-tier.md](../../docs/architecture/decisions/0014-serving-profile-and-secondary-tier.md) | Añadimos una nota de vigencia que distingue preset, configuración efectiva y evaluación histórica. |
| [docs/architecture/overview.md](../../docs/architecture/overview.md) | Actualizamos los dos flujos exigidos: consulta e ingesta, con decisiones, errores, permisos y estado. |
| [docs/arquitectura-agentica.md](../../docs/arquitectura-agentica.md) | Añadimos una advertencia histórica y enlaces a la arquitectura vigente. |
| [docs/arquitecturas-rag-y-contribucion.md](../../docs/arquitecturas-rag-y-contribucion.md) | Identificamos el análisis como histórico y enlazamos los contratos vigentes. |
| [docs/contracts/README.md](../../docs/contracts/README.md) | Actualizamos la relación entre Source, Answer y la evidencia añadida, manteniendo el contrato académico. |
| [docs/contracts/access-and-guardrails.md](../../docs/contracts/access-and-guardrails.md) | Describimos los controles implementados y sus límites en lugar de presentarlos como trabajo pendiente. |
| [docs/contracts/generation.md](../../docs/contracts/generation.md) | Precisamos generación extractiva, Haiku, fallback, citas y límites del control de presupuesto. |
| [docs/contracts/pipeline.md](../../docs/contracts/pipeline.md) | Documentamos etapas, respuesta y evidencia finales, llamadas, degradaciones y sanitización. |
| [docs/course/README.md](../../docs/course/README.md) | Añadimos el índice de entregables, maquetación reproducible y correspondencia del PDF de 15 páginas, incluida la carátula, con su fuente. |
| [docs/course/auditoria-cumplimiento.md](../../docs/course/auditoria-cumplimiento.md) | Creamos la matriz de requisitos y evidencias; incorporamos esta explicación por archivo y el registro de limpieza. |
| [docs/course/defensa.md](../../docs/course/defensa.md) | Preparamos quince minutos de demostración con consultas concretas, control de abstención y análisis de una falla. |
| [docs/course/informe-final.md](../../docs/course/informe-final.md) | Redactamos el informe académico en primera persona plural, distinguiendo resultados actuales, históricos y actividades pendientes. |
| [docs/course/informe.md](../../docs/course/informe.md) | Completamos las dieciséis secciones de la plantilla de anteproyecto, conservando integrantes y carnets. |
| [docs/data/sensitive-data.md](../../docs/data/sensitive-data.md) | Ajustamos la descripción de redacción, persistencia y retención a los controles implementados. |
| [docs/data/sources.md](../../docs/data/sources.md) | Actualizamos fuentes, siete juegos, snapshots y condiciones de licencia por origen. |
| [docs/deployment/README.md](../../docs/deployment/README.md) | Corregimos puertos, perfiles y preparación; documentamos Docker y las 36 comprobaciones HTTP sin conexión al LLM. |
| [docs/evaluation/agentic-ablation.md](../../docs/evaluation/agentic-ablation.md) | Añadimos la identificación histórica, conservando las cifras de ablación. |
| [docs/evaluation/audit-current.md](../../docs/evaluation/audit-current.md) | Consolidamos mediciones actuales, fallas, procedencia y comandos de reproducción. |
| [docs/evaluation/metrics.md](../../docs/evaluation/metrics.md) | Precisamos denominadores, hit rate, recall, abstención, P95 y evaluación contextual; retiramos atribuciones humanas sin evidencia. |
| [docs/evaluation/results.md](../../docs/evaluation/results.md) | Identificamos las tablas históricas y enlazamos las mediciones actuales sin alterar las cifras originales. |
| [docs/evaluation/scorecard-base.md](../../docs/evaluation/scorecard-base.md) | Añadimos el marcador del perfil base con procedencia y metas cumplidas, incumplidas o no evaluables. |
| [docs/evaluation/scorecard.md](../../docs/evaluation/scorecard.md) | Regeneramos la presentación del marcador histórico con procedencia y metas separadas de regresiones. |
| [docs/evaluation/test-bank.md](../../docs/evaluation/test-bank.md) | Actualizamos categorías, revisiones documentales y oráculos; aclaramos la procedencia de anotaciones. |
| [docs/informe-estado.md](../../docs/informe-estado.md) | Marcamos el informe como histórico y enlazamos el estado vigente. |
| [docs/ingestion/README.md](../../docs/ingestion/README.md) | Actualizamos la preparación de siete juegos y ambos corpus mediante bootstrap. |
| [docs/ingestion/chunking.md](../../docs/ingestion/chunking.md) | Precisamos parámetros actuales y tratamiento de contenido sensible; identificamos mediciones históricas. |
| [docs/ingestion/cleaning.md](../../docs/ingestion/cleaning.md) | Acotamos el inventario inicial y sus cifras, documentamos otras plataformas y retiramos la atribución de una revisión manual nueva. |
| [docs/ingestion/metadata.md](../../docs/ingestion/metadata.md) | Documentamos campos reales, herencia de quest, revisión, ubicación, hashes y extractos. |
| [docs/memoria-y-tecnicas-avanzadas.md](../../docs/memoria-y-tecnicas-avanzadas.md) | Identificamos el documento exploratorio como histórico y enlazamos las capacidades vigentes. |
| [docs/overview/games.md](../../docs/overview/games.md) | Actualizamos los siete juegos, sus modelos de progreso y diferencias de cobertura. |
| [docs/overview/problem-and-scope.md](../../docs/overview/problem-and-scope.md) | Ajustamos usuarios, alcance y capacidades reales, separando metas de requisitos y trabajo futuro. |
| [docs/retrieval/README.md](../../docs/retrieval/README.md) | Actualizamos BM25, E5, RRF, filtros y búsqueda secundaria, distinguiendo resultados históricos. |
| [docs/retrieval/bm25.md](../../docs/retrieval/bm25.md) | Aclaramos que BM25 participa en la recuperación híbrida implementada y rotulamos las ablaciones históricas. |
| [docs/retrieval/query-expansion.md](../../docs/retrieval/query-expansion.md) | Diferenciamos expansión por glosario de reescritura LLM implementada y contextualizamos sus mediciones históricas. |
| [docs/retrieval/semantic.md](../../docs/retrieval/semantic.md) | Corregimos instalación con extras y documentamos invalidación de índices por cambios de metadatos. |
| [docs/roadmap.md](../../docs/roadmap.md) | Sustituimos pendientes obsoletos por implementación y comprobaciones realizadas, con los pendientes reales. |
| [docs/security/controls.md](../../docs/security/controls.md) | Actualizamos amenazas, controles, oráculos y resultados; distinguimos exposición de texto de obediencia de un LLM. |
| [docs/security/report.md](../../docs/security/report.md) | Regeneramos el reporte final con sus 37/42 casos, oráculos, cuarentena y fallas de abstención. |
| [docs/tools/README.md](../../docs/tools/README.md) | Documentamos evidencia por filas autorizadas, comprobación de fuentes y límites del flujo de revisión humana. |
| [docs/ui/README.md](../../docs/ui/README.md) | Describimos evidencia exacta, resultados históricos rotulados e inspección de Gradio, sin atribuir pruebas de accesibilidad no realizadas. |
| [eval/fixtures/README.md](../../eval/fixtures/README.md) | Explicamos el corpus sintético y los cambios de criterio entre versiones de los oráculos. |
| [data/wiki_snapshot/README.md](../../data/wiki_snapshot/README.md) | Acotamos la atribución inicial a StrategyWiki y remitimos a las condiciones separadas de las fuentes incorporadas después. |

### Pruebas

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [tests/test_api.py](../../tests/test_api.py) | Comprobamos evidencia con y sin traza y la página original de búsqueda. |
| [tests/test_bootstrap.py](../../tests/test_bootstrap.py) | Verificamos preparación, reutilización, reparación e invalidación de corpus y manejo de configuración. |
| [tests/test_content_policy.py](../../tests/test_content_policy.py) | Verificamos spoilers, filas, escenas, quests y cuarentena; añadimos celdas de mapa, ordinales, rangos, rutas dependientes y cortes parciales, con controles de utilidad. |
| [tests/test_contracts.py](../../tests/test_contracts.py) | Rechazamos citas cuyo identificador coincida pero cuya fuente o página sea falsa. |
| [tests/test_evaluation_artifacts.py](../../tests/test_evaluation_artifacts.py) | Verificamos evidencia, hashes, comparabilidad, metadatos seguros, juez, métricas y revisiones documentales. |
| [tests/test_games.py](../../tests/test_games.py) | Conservamos la comprobación de dieciocho mazmorras al ampliar el reconocimiento de quests. |
| [tests/test_graph.py](../../tests/test_graph.py) | Adaptamos la equivalencia entre pipeline y grafo a nuevas etapas y respuesta final, excluyendo tiempos variables. |
| [tests/test_llm_budget.py](../../tests/test_llm_budget.py) | Comprobamos concurrencia de presupuesto, aislamiento de telemetría y cierre de conexiones SQLite. |
| [tests/test_profile.py](../../tests/test_profile.py) | Verificamos claves vacías, perfil full desde la plantilla y precedencia de overrides explícitos. |
| [tests/test_request_evidence.py](../../tests/test_request_evidence.py) | Verificamos evidencia secundaria exacta, concurrencia, reintentos, fallback, auditoría e invalidación por metadatos. |
| [tests/test_tools.py](../../tests/test_tools.py) | Exigimos que respuesta y evidencia oculten las mismas filas y que se compruebe la fuente original. |
| [tests/test_ui_puesto.py](../../tests/test_ui_puesto.py) | Verificamos metas del artefacto, rotulado histórico, enlaces seguros y ausencia de una segunda búsqueda. |

### Bancos y configuración de evaluación

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [eval/cases_versions.jsonl](../../eval/cases_versions.jsonl) | Definimos las preguntas y expectativas para las revisiones documentales sintéticas. |
| [eval/fixtures/document_versions.json](../../eval/fixtures/document_versions.json) | Conservamos los dos estados de un documento sintético con el dato que cambia de revisión. |
| [eval/security_content_oracle.jsonl](../../eval/security_content_oracle.jsonl) | Conservamos el criterio inicial de spoilers para que su medición histórica siga siendo interpretable. |
| [eval/security_content_oracle_v2.jsonl](../../eval/security_content_oracle_v2.jsonl) | Definimos expectativas independientes sobre soluciones, ubicaciones futuras y utilidad permitida. |
| [eval/security_quest_oracle.jsonl](../../eval/security_quest_oracle.jsonl) | Conservamos la sonda exploratoria inicial de separación entre quests. |
| [eval/security_quest_oracle_v2.jsonl](../../eval/security_quest_oracle_v2.jsonl) | Añadimos control positivo de contenido útil e impedimos mezcla de quests. |
| [eval/scorecard_manifest_base.json](../../eval/scorecard_manifest_base.json) | Identificamos los resultados finales y bancos que alimentan el marcador base. |

### Resultados y entregables conservados

Las cifras de los artefactos siguientes pertenecen al cierre previo al refuerzo de mapas. La palabra «final» en sus nombres identifica aquella etapa y no una nueva ejecución con el código posterior. El PDF y su manifiesto se actualizan mediante el proceso de maquetación documentado.

| Archivo | Cambio concreto y propósito |
| --- | --- |
| [eval/results/2026-11-16_http-closure-offline.json](../../eval/results/2026-11-16_http-closure-offline.json) | Conservamos las 36 comprobaciones HTTP del cierre previo, configuración offline y evidencia exacta. No incluye los siete casos posteriores de mapas. |
| [eval/results/2026-11-16_pytest-closure.xml](../../eval/results/2026-11-16_pytest-closure.xml) | Guardamos el resultado de 489 pruebas aprobadas, sin omisiones; no es un archivo de compilación. |
| [eval/results/20261116T020916693613Z-6a1d9df6_versions_synthetic-document-revisions.json](../../eval/results/20261116T020916693613Z-6a1d9df6_versions_synthetic-document-revisions.json) | Respaldamos los dos casos de revisión documental ejecutados con BM25. |
| [eval/results/20261116T021416021518Z-bdb13499_oracle_content-oracle.json](../../eval/results/20261116T021416021518Z-bdb13499_oracle_content-oracle.json) | Conservamos el resultado inicial 5/8 y sus fallas bajo el criterio original del oráculo. |
| [eval/results/20261116T021551449635Z-0f516a70_e2e_audit-base-principal.json](../../eval/results/20261116T021551449635Z-0f516a70_e2e_audit-base-principal.json) | Conservamos la corrida anterior para demostrar la pérdida de un acierto en zelda_robust_06. |
| [eval/results/20261116T021731134543Z-c9bec733_oracle_content-oracle.json](../../eval/results/20261116T021731134543Z-c9bec733_oracle_content-oracle.json) | Conservamos el resultado 7/9 bajo el criterio explícito de la segunda versión del oráculo. |
| [eval/results/20261116T022250583253Z-b13d858d_versions_synthetic-document-revisions.json](../../eval/results/20261116T022250583253Z-b13d858d_versions_synthetic-document-revisions.json) | Respaldamos los dos casos de revisión documental ejecutados con el modelo denso E5. |
| [eval/results/20261116T022631268527Z-2ffd3153_e2e_audit-final-base-principal.json](../../eval/results/20261116T022631268527Z-2ffd3153_e2e_audit-final-base-principal.json) | Guardamos las 54 consultas finales del banco principal con configuración, evidencia, resultados y hashes. |
| [eval/results/20261116T022649868252Z-e9fc6355_e2e_audit-final-base-hard.json](../../eval/results/20261116T022649868252Z-e9fc6355_e2e_audit-final-base-hard.json) | Guardamos las 21 consultas finales del banco difícil y sus fallas de abstención. |
| [eval/results/20261116T022651099719Z-d06db1c2_e2e_audit-final-base-extra.json](../../eval/results/20261116T022651099719Z-d06db1c2_e2e_audit-final-base-extra.json) | Guardamos las 61 consultas del banco adicional, mostrando la falta de cobertura secundaria del perfil base. |
| [eval/results/20261116T022654688800Z-b171d853_security_guarded.json](../../eval/results/20261116T022654688800Z-b171d853_security_guarded.json) | Guardamos la suite final con controles: 37/42, oráculos de contenido y quests y pruebas de cuarentena. |
| [eval/results/20261116T022700230687Z-c9546ebd_security_baseline.json](../../eval/results/20261116T022700230687Z-c9546ebd_security_baseline.json) | Guardamos el control final sin las protecciones evaluadas para comparar bajo el mismo banco. |
| [eval/results/20261116T022858581774Z-3a5bc434_tools_tools.json](../../eval/results/20261116T022858581774Z-3a5bc434_tools_tools.json) | Guardamos 26/26 casos de herramientas y la comprobación de falsos disparos del router. |
| [eval/results/scorecard_base_current.json](../../eval/results/scorecard_base_current.json) | Consolidamos métricas, procedencia y cumplimiento de metas del perfil base para acompañar el marcador Markdown. |
| [eval/results/scorecard_latest.json](../../eval/results/scorecard_latest.json) | Actualizamos el resumen histórico consumido por la API y Gradio, incluyendo procedencia y metas explícitas. |
| [output/pdf/informe-final.pdf](../../output/pdf/informe-final.pdf) | Exportamos el informe final de 15 páginas, incluida la carátula, con tablas y dos diagramas. |
| [output/pdf/informe-final.layout.json](../../output/pdf/informe-final.layout.json) | Vinculamos PDF y Markdown mediante hashes y registramos páginas y figuras; permite comprobar la exportación entregada. |

### Registro histórico de la limpieza realizada

Retiramos siete JSON recientes sustituidos por verificaciones finales. Ninguno era un archivo previamente versionado ni estaba enlazado como evidencia por los informes, manifiestos o código.

| Archivo eliminado de eval/results/ | Motivo |
| --- | --- |
| `2026-11-16_http-closure.json` | Comprobación anterior reemplazada por la versión offline final, que también registra 36/36. |
| `20261116T021552608237Z-4cf618a0_e2e_audit-base-hard.json` | Corrida intermedia del banco difícil reemplazada por la final. |
| `20261116T021554450318Z-baf3e0c5_e2e_audit-base-extra.json` | Corrida intermedia del banco adicional reemplazada por la final. |
| `20261116T021952800302Z-684fbf1e_security_guarded.json` | Diagnóstico anterior a las últimas correcciones de quests y cuarentena. |
| `20261116T021957500680Z-dc430428_security_baseline.json` | Control intermedio sustituido por el baseline final comparable. |
| `20261116T022042517009Z-5c5cb6a8_tools_tools.json` | Evaluación de herramientas reemplazada por la corrida final, también 26/26. |
| `20261116T022336668107Z-d80b6931_oracle_content-oracle.json` | Sonda exploratoria de quests reemplazada por el oráculo final con control positivo de utilidad. |

Eliminamos además 761 archivos locales regenerables: 628 en `.pytest_cache/` —incluidos 175 JSON de fixtures temporales—, cinco en `.ruff_cache/`, 38 intermedios de maquetación en `tmp/pdfs/` y 90 archivos de bytecode en carpetas `__pycache__/` de código y pruebas. Estas carpetas ya estaban excluidas por Git. En conjunto retiramos 768 archivos, aproximadamente **20.1 MiB**, y redujimos los archivos nuevos visibles en Git de 50 a 43.

Conservamos trece JSON nuevos de resultados: nueve finales o consolidados y cuatro registros necesarios para interpretar comparaciones y cambios de criterio. Entre estos últimos están la corrida principal anterior a la regresión, las dos versiones del oráculo de contenido y la comprobación de revisiones con BM25. Preservamos también todos los resultados históricos previamente versionados.

### Por qué conservamos otros JSON

| Ubicación | Función |
| --- | --- |
| `eval/results/` | Evidencia de mediciones y resúmenes que respaldan informes o alimentan la interfaz. |
| `eval/scorecard_manifest*.json` | Identificación de bancos y corridas utilizadas para calcular cada marcador. |
| `eval/fixtures/document_versions.json` y bancos JSONL | Entradas de pruebas y expectativas de evaluación. |
| `data/wiki_snapshot/**/manifest.json` | Procedencia, archivo y revisión de los documentos del corpus. |
| `data/seed/profiles.json` | Perfiles iniciales de la demostración. |
| `src/gamerag/ui/tokens.json` | Configuración visual utilizada por la interfaz. |
| `output/pdf/informe-final.layout.json` | Correspondencia verificable entre el informe Markdown y el PDF entregado. |
| `data/processed/` y `models/` | Artefactos locales ya ignorados por Git; sus metadatos permiten reutilizar corpus y cargar modelos. |

La extensión JSON no determina si un archivo es prescindible. Mantenemos los datos funcionales y la evidencia necesaria para reproducir o comprobar la entrega. Durante aquella limpieza no modificamos el informe final ni su PDF; la revisión documental posterior requiere su propia exportación.

Inmediatamente después de aquella limpieza verificamos las 125 rutas incluidas entonces en el inventario, la validez de los JSON y JSONL afectados, los dos manifiestos de evaluación y los enlaces locales. Ruff y la comprobación de regresiones del scorecard histórico terminaron sin errores. El manifiesto de maquetación identifica los hashes de cada exportación; se debe comprobar nuevamente su correspondencia cuando cambia la fuente del informe.
