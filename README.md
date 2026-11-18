# GameRAG: consultas documentales de videojuegos con control de spoilers

Proyecto final de **CC3103 Procesamiento de Lenguaje Natural**, Universidad del Valle de Guatemala, ciclo 2-2026.

GameRAG recupera evidencia de snapshots de wikis, responde con citas verificables y aplica restricciones de juego y progreso. El corpus configura siete juegos: The Legend of Zelda, Ninja Gaiden (NES), Ocarina of Time, Assassin's Creed II, Doom, Grand Theft Auto: San Andreas y Red Dead Redemption. La evaluación principal se concentra en los dos primeros; ampliar el corpus no equivale a validar por igual todos los juegos.

La interfaz vigente es **Puesto de Control**, construida con **Gradio**, en `http://127.0.0.1:7860`. Consume una API FastAPI en `http://127.0.0.1:8000`. Los perfiles son de demostración y se seleccionan mediante `user_id`; el proyecto no incorpora autenticación de producción.

## Qué hace y cómo observarlo

El usuario formula una pregunta sobre el juego elegido. GameRAG busca pasajes de las guías, aplica las restricciones del perfil y entrega una respuesta acompañada de la evidencia utilizada. Por ejemplo, un jugador que está en el nivel 2 puede consultar su jefe; preguntar por el nivel 7 permite observar el bloqueo por progreso. Cambiar al perfil `completionist` permite comparar el acceso.

Utilizamos modelos preentrenados: E5 representa el significado de las consultas y Haiku puede redactar respuestas desde la evidencia. El perfil inicial `base` funciona sin clave ni llamadas al LLM y muestra extractos de las fuentes. El perfil `full` habilita la generación remota y el flujo de evaluación y recuperación secundaria.

## Instalación local

Requisito de entrada: [uv](https://docs.astral.sh/uv/) instalado. El proyecto fija Python 3.12 en `.python-version`; el siguiente comando selecciona esa versión y puede descargarla si no está instalada. Ejecutar desde la raíz del repositorio:

```powershell
uv sync --locked --python 3.12 --extra semantic --extra ui
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run --no-sync python --version
```

En Linux/macOS, realizar la copia con `cp .env.example .env` solo si `.env` no existe. Conservar las credenciales locales y no incluir `.env` en commits. Los extras se seleccionan juntos porque una sincronización posterior sin ellos puede retirar dependencias del entorno. Utilizar `uv run --no-sync` para ejecutar el Python del proyecto, aunque el comando global `python` apunte a una versión antigua. `.venv/` y `.env` son locales y están excluidos por Git.

### Preparar el corpus

Los snapshots versionados permiten repetir la ingesta sin volver a descargar las wikis.

El comando recomendado prepara lo necesario según el perfil efectivo y reutiliza artefactos solo si su huella sigue vigente:

```powershell
uv run --no-sync python -m gamerag.bootstrap
```

Para reconstruir explícitamente ambos conjuntos de los siete juegos:

```powershell
$gameIds = 'zelda1','ninja_gaiden_nes','oot','ac2','doom','gta_sa','rdr1'
foreach ($gameId in $gameIds) {
    uv run --no-sync python -m gamerag.ingest.build $gameId --chunker structural
    uv run --no-sync python -m gamerag.ingest.build $gameId --chunker structural --sources all
}
```

`chunks.structural.jsonl` contiene la fuente primaria; `chunks.structural-multi.jsonl` incorpora fuentes adicionales. La recuperación secundaria aplica además el alcance configurado: las fuentes de toda una franquicia no se incluyen por defecto. Detalle en [ingesta](docs/ingestion/README.md) y [fuentes](docs/data/sources.md).

### Arrancar API e interfaz

En dos terminales, con el entorno ya sincronizado:

```powershell
uv run --no-sync uvicorn gamerag.api:app
```

Esperar a que [el estado de la API](http://127.0.0.1:8000/health) responda con `status: ok`. Después, abrir la segunda terminal en la raíz del repositorio:

```powershell
uv run --env-file .env --no-sync python -m gamerag.ui.puesto
```

Abrir **[Puesto de Control](http://127.0.0.1:7860)**. Mantener ambas terminales abiertas; `Ctrl+C` en cada una detiene su servicio. Si Gradio se inició antes de la API y aparece sin juegos, reiniciar el proceso de la interfaz después de comprobar `/health`.

Consultar [la documentación HTTP](http://127.0.0.1:8000/docs) para inspeccionar el contrato. El modelo de embeddings se descarga en el primer uso de recuperación semántica; las ejecuciones posteriores pueden reutilizar `models/`. La opción `--env-file .env` entrega las variables locales a Gradio, que las consulta directamente desde el entorno.

### Primera prueba en la interfaz

1. En **Ventanilla**, seleccionar **The Legend of Zelda (1986)** y el perfil **novato**.
2. Mantener desmarcado **Solo buscar (sin generar)**.
3. Escribir `What is the white sword?` en **Consulta del viajero** y pulsar **Entregar**.
4. Abrir las referencias para ver el texto utilizado, su sección y revisión. En `base` la respuesta presenta extractos.
5. Probar `Who is the boss of level 2?` para observar una respuesta mediante la herramienta de hechos.
6. Probar `Who is the boss of level 7 in the first quest?` con `novato` y después con `completionist` para comparar permisos.

Empezar con preguntas en inglés: el corpus principal y los bancos de validación utilizan ese idioma. Las preguntas son independientes; no hay memoria conversacional persistente. El [recorrido de uso](docs/ui/README.md) explica los perfiles, pruebas de seguridad, auditoría y marcador de resultados.

## Perfiles de ejecución

| Perfil | Recuperación y generación | Requisitos |
| --- | --- | --- |
| `base` | Híbrida BM25 + E5, generador extractivo, router y controles de acceso | Extra `semantic`; no requiere llamadas al LLM |
| `full` | Grafo de estado, Haiku, evaluación de evidencia cuando hay abstención y segunda búsqueda mixta | Extra `semantic`, corpus adicional y clave no vacía para activar el preset; clave aceptada por el proveedor para generar remotamente |

`GAMERAG_PROFILE` selecciona el perfil; las opciones explícitas de `.env` prevalecen. El modo efectivo debe verificarse en `/health`: una clave ausente o vacía no demuestra una ejecución con Haiku. Para una línea base ligera puede fijarse `GAMERAG_RETRIEVER=bm25` y `GAMERAG_GENERATOR=extractive`. Planificador y notas de memoria son experimentales y permanecen desactivados por defecto; no hay memoria conversacional persistente.

Los presupuestos, precios y modelo son parámetros locales. Los costos publicados son estimaciones calculadas con la configuración de cada ejecución, no una cotización vigente del proveedor.

Para probar generación remota, editar `.env` con una clave válida en `ANTHROPIC_API_KEY`, fijar `GAMERAG_PROFILE=full` y `GAMERAG_LLM_OFFLINE=false`, ejecutar nuevamente `gamerag.bootstrap` y reiniciar ambos servicios. Comprobar en `/health.configuration` el generador, grafo y búsqueda secundaria. Si el proveedor falla, se registra la degradación; una respuesta extractiva no demuestra que Haiku se haya ejecutado.

## Docker

```powershell
docker compose up --build
```

API: `http://localhost:8000/docs`. Interfaz: `http://localhost:7860`. Compose conserva modelos, índices, chunks y estado en cuatro volúmenes. Véase [despliegue](docs/deployment/README.md).

## Evaluación y trazabilidad

```powershell
uv run --no-sync python -m gamerag.evaluation.retrieval zelda1 --retriever bm25 --chunker structural
uv run --no-sync python -m gamerag.evaluation.tools_eval --help
uv run --no-sync python -m gamerag.evaluation.e2e --help
uv run --no-sync pytest
uv run --no-sync ruff check .
```

La API y los evaluadores reutilizan el pipeline, pero un benchmark directo del pipeline no mide transporte HTTP ni renderizado de Gradio. La evidencia exacta de `/ask` se devuelve en `evidence`; no debe reconstruirse con otra búsqueda. La traza registra respuesta final, evidencia autorizada, decisiones, llamadas al modelo y degradaciones. Véanse [contratos](docs/contracts/README.md) y [evaluación](docs/evaluation/metrics.md).

Los resultados históricos se conservan en `eval/results/`. La [hoja de ruta](docs/roadmap.md) distingue implementación, verificación y pendientes. Un resultado sin regresiones no acredita por sí mismo el cumplimiento de todas las metas ni la ausencia general de spoilers.

La evaluación base del cierre previo cubre 136 consultas sin llamadas LLM; registra fallas de abstención y utilidad, además de precisión de citas inferior a la meta. Esas corridas preceden a la ampliación del filtro de mapas de Hyrule. Los resultados y comandos están en la [auditoría de evaluación](docs/evaluation/audit-current.md), el [informe final](docs/course/informe-final.md) y la [matriz de cumplimiento](docs/course/auditoria-cumplimiento.md). Ni esas cifras ni los históricos con Haiku se presentan como una evaluación nueva del código actualizado.

La verificación posterior a la corrección de mapas superó **520 pruebas sin omisiones**, Ruff y siete comprobaciones HTTP locales: respuesta y evidencia por perfil, búsqueda y herramienta. También se comprobó en Gradio el extracto autorizado de Hyrule 3. Los artefactos del cierre previo conservan [489 pruebas](eval/results/2026-11-16_pytest-closure.xml) y [36 comprobaciones HTTP](eval/results/2026-11-16_http-closure-offline.json); no contienen la ejecución posterior. En aquel cierre se verificó el arranque limpio de Docker con el preset `full`, BM25 explícito, clave ficticia inválida y modo offline. Las verificaciones descritas no realizaron llamadas remotas al LLM.

## Documentación y entregables

| Ruta | Contenido |
| --- | --- |
| [docs/](docs/README.md) | Guía del sistema y evidencias |
| [Anteproyecto](docs/course/informe.md) | Plantilla consolidada en sus 16 secciones |
| [Informe técnico final](docs/course/informe-final.md) | Diseño, metodología, resultados, límites y uso de IA |
| [Maquetación académica](docs/course/README.md) | Comando portable para generar PDF y comprobar sus páginas |
| [Guion de defensa](docs/course/defensa.md) | Demostración y defensa de 15 minutos |
| [Presentación del equipo](docs/course/presentacion-equipo.pdf) | Diapositivas del proyecto |
| [Video de presentación](https://youtu.be/ZC5XwdeHOQ4) | Presentación audiovisual del equipo |
| [config/games/](config/games/) | Progreso, fuentes y herramientas por juego |
| [data/wiki_snapshot/](data/wiki_snapshot/README.md) | Snapshots, manifiestos de revisión y atribución |
| [src/gamerag/](src/gamerag/) | Ingesta, recuperación, generación, controles, API e interfaz |
| [tests/](tests/) | Pruebas automatizadas |

Para generar el PDF desde la raíz, con Graphviz (`dot`) en `PATH`:

```powershell
uv run --no-sync --with reportlab --with pypdf --with pillow python scripts/render_report.py docs/course/informe-final.md output/pdf/informe-final.pdf
```

La exportación genera un manifiesto de páginas y hashes. El PDF debe regenerarse cuando cambie el Markdown y revisarse visualmente antes de entregar.

## Licencias

El código se distribuye bajo [MIT](LICENSE). Los textos conservan las licencias y atribuciones de sus fuentes; existen contenidos CC BY-SA y GFDL en carpetas separadas. No debe asumirse una licencia única para todo el corpus. Los manifiestos registran URL y revisión por página; [fuentes y gobernanza](docs/data/sources.md) recoge las condiciones declaradas. Los manuales comerciales no forman parte del corpus distribuido.
