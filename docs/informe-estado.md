# Informe de estado y propuesta de evolución

Fecha: 2026-11-07 · Rama `main` · Basado en el código, `docs/` y `eval/` del repositorio.

## 1. Resumen ejecutivo

- **Lo que hay es más que un RAG simple en la parte de recuperación, pero menos de lo que parece en la parte de generación.** La recuperación ya es híbrida (BM25 + embeddings e5, fusión RRF plana), con multi-consulta (ortografía + glosario), alias de ubicación y tokens de frase. Alcanza Recall@5 0.94 en el set del curso. Hay también un router de intención por reglas y tres herramientas, una API con auditoría, Docker y CI.
- **Pero no hay generación real.** El generador es *extractivo* (devuelve los 3 fragmentos más relevantes recortados). `HaikuGenerator` no existe todavía: la "A" y la "G" de RAG están pendientes. Por eso, de cara a quien lo use, el sistema se siente como "búsqueda con citas", no como un asistente.
- **No hay ninguna métrica de generación, de operación (latencia P95, tokens, costo) ni de seguridad.** En la rúbrica del curso, Evaluación (15) y Seguridad (15) pesan 30 puntos, y hoy solo está cubierta la mitad de Evaluación (recuperación).
- **La UI es Streamlit mínima**, hecha explícitamente como herramienta de demo y depuración. No tiene streaming ni conversación de varios turnos.
- **Recomendación:** antes de agregar tecnología nueva, cerrar el ciclo extremo a extremo (generación con Haiku + evaluación de generación). Después, las mejoras de estado del arte con mayor retorno para este corpus son *Contextual Retrieval*, reescritura de consulta con LLM, un flujo agéntico con verificación de suficiencia (con LangGraph) y un grafo/tabla de entidades. Para la UI: NiceGUI montado sobre la misma FastAPI, más un endpoint compatible con OpenAI para poder conectar Open WebUI sin costo.

## 2. Estado actual

### 2.1 Qué está hecho

| Área | Estado | Evidencia |
| --- | --- | --- |
| Corpus | 2 juegos (Zelda, Ninja Gaiden), snapshot de StrategyWiki con `revid`, CC BY-SA | `data/wiki_snapshot/`, ADR-0002 |
| Ingesta | Limpieza de wikitext, secciones, chunking estructural, metadatos de ubicación | `src/gamerag/ingest/` (~730 líneas) |
| Recuperación | BM25 + denso (e5-small multilingüe, coseno exacto) + RRF plana + multi-consulta + alias de ubicación | ADR-0009 a 0012 |
| Router y herramientas | `query_game_facts` (SQL de solo lectura), `next_available_levels`, `update_progress` (exige confirmación humana) | ADR-0013, `src/gamerag/tools/` |
| Contratos | `Generator`, `AccessFilter`, `InputGuard`/`OutputGuard`, `Answer` (Pydantic §11) | `docs/contracts/` |
| Guardrails | G1 (por juego), citas ⊆ contexto, juego correcto, validación de esquema y longitud | `guardrails/base.py` |
| API | FastAPI: `/ask`, `/search`, `/audit`, perfiles; SQLite; PII redactada en auditoría | `api.py`, `store.py` |
| UI | Streamlit mínima: juego, perfil, pregunta, contexto, traza, auditoría | `ui/app.py` (158 líneas) |
| Despliegue | Dockerfile + compose (`api` + `ui`), 4 volúmenes | verificado de punta a punta |
| CI | lint + tests con uv en cada push a `main` | `.github/workflows/ci.yml` |
| Docs | 13 ADR, contratos, resultados detallados | `docs/` |

**Código:** ~3.200 líneas en `src/`, ~1.450 en `tests/`.

**Tests (corrida de hoy en Windows):** 250 pasan, 5 se saltan, **16 dan error** (`PermissionError [WinError 5]` en `test_api.py` y `test_ui_client.py`). No diagnostiqué la causa: parece un problema de permisos del entorno al crear la base SQLite o un directorio temporal, no una falla de lógica, pero hay que confirmarlo corriendo `uv run pytest` en tu terminal.

### 2.2 Resultados de recuperación (configuración servida)

| Conjunto | n | Recall@5 | Nota |
| --- | ---: | ---: | --- |
| Curso (Zelda) | 18 | 0.94 | Línea base BM25 + chunking fijo: 0.78 |
| Equipo (Zelda) | 8 | 1.00 | Tras corregir la etiqueta de `team_08` |
| Total Zelda | 36 | 0.97 | MRR 0.70; sin el "?" final: 0.94 |
| Ninja Gaiden | 13 | 0.92 | Sin glosario: 0.85 |

Banco: 54 casos (49 con respuesta, 5 sin respuesta) en `eval/cases.jsonl`.

### 2.3 Qué falta (según `docs/roadmap.md`)

| Pendiente | Peso en rúbrica | Quién (según el roadmap) |
| --- | --- | --- |
| `HaikuGenerator`: prompt de contexto cerrado, citas, abstención | Implementación NLP/RAG (15) | Otro integrante |
| Evaluación de generación: fidelidad, precisión de citas, abstención, tokens, costo, P95 | Evaluación (15) | Otro integrante |
| Gates G2 (quest), G2b (segmentos de NG), G3 (entidades de solución), G4 | Seguridad / propuesta de valor | Otro integrante |
| Detector de inyección de prompt y PII en la entrada | Seguridad (15) | Otro integrante |
| Pruebas adversarias y reporte de seguridad (`docs/security/`) | Seguridad (15) | Otro integrante |
| Diagrama formal de arquitectura (§6) | Arquitectura (15) | Pendiente |
| Documento técnico de 10 a 15 páginas, demo, presentación | Entregables | Pendiente |
| Español (opcional) | Extra | Trabajo futuro |

## 3. Diagnóstico honesto

1. **El banco de evaluación es chico y está parcialmente "visto".** El glosario de Zelda se escribió conociendo los fallos; el de Ninja Gaiden, con 15 casos de un solo autor, donde un caso vale 0.077. Los números de 0.92 a 0.97 sirven para comparar variantes, no para prometer desempeño real. El propio `results.md` lo advierte.
2. **Las ablaciones están bien hechas** (se probó y se descartó reranker, chunking por fila y reglas de identificadores). Eso es un activo para la defensa. Pero las conclusiones sobre el reranker valen para MiniLM, no para los reranker modernos (ver 4.3).
3. **La abstención no se puede decidir con los scores de recuperación** (las distribuciones se superponen). Eso fue un buen hallazgo y obliga a que lo decida un LLM juzgando si el contexto responde. Hoy nadie lo hace.
4. **El glosario a mano no escala.** Cada juego nuevo necesita su glosario, y es un parche de vocabulario (*attack* ↔ *swing the sword*). Es justo el problema que un LLM resuelve mejor y de forma más general.
5. **La dilución de embeddings sigue siendo el fallo dominante** (`heal` en NG, tablas de ítems). Es el problema que ataca *Contextual Retrieval*.
6. **Una sola vuelta, un solo turno.** No hay conversación ("¿y cómo llego ahí?") ni reintento si la evidencia es mala.
7. **Hay que coordinar con el equipo:** generación, gates, seguridad y diseño final de UI están asignados a otros integrantes. Las propuestas de abajo marcan dónde se tocaría lo de ellos.

## 4. Mejoras de RAG hacia el estado del arte

Criterio de selección: que **encaje con un corpus pequeño** (~250 chunks por juego), que se pueda **medir con una ablación** como ya hacen, y que **se pueda defender** en 15 minutos. No todo lo "moderno" ayuda aquí; lo marco.

Esfuerzo: S = 1 día o menos, M = 2 a 4 días, L = más de una semana.

### 4.1 Prioridad alta (cierra huecos y rinde más)

| # | Mejora | Qué resuelve en este proyecto | Esfuerzo |
| --- | --- | --- | :-: |
| 1 | **Generación con Haiku, con salida estructurada y citas** (tool-use forzado al esquema `Answer`, o la API de Citations de Anthropic), abstención juzgada por el modelo, *prompt caching* del prompt de sistema, streaming | Cierra la "A" y la "G". Habilita todas las métricas de respuesta. Mantener `FallbackGenerator` | M |
| 2 | **Evaluación de generación**: fidelidad y relevancia con LLM-as-judge (RAGAS o DeepEval, o un juez propio con rúbrica), precisión de citas, tasa de abstención, tokens, costo, P95. Intervalos de confianza por bootstrap | Cubre la mitad faltante de Evaluación (15 pts) y la comparación línea base vs mejorada | M |
| 3 | **Contextual Retrieval** (Anthropic): un LLM antepone a cada chunk una frase de contexto ("Este fragmento es de la lista de ítems de Ninja Gaiden, sobre la poción de salud…") antes de indexar en BM25 y en embeddings | Ataca directamente la dilución y el desajuste de vocabulario. Anthropic reporta reducciones grandes de fallos de recuperación; hay que medirlo aquí. Costo bajo: ~330 chunks, y con prompt caching casi nada | S–M |
| 4 | **Reescritura de consulta con LLM** (multi-consulta, descomposición de preguntas compuestas, *step-back*; HyDE como variante) en lugar de o junto al glosario a mano | Generaliza a juegos nuevos sin glosario. Se compara contra el glosario actual (ablación). Riesgo: latencia y costo por pregunta; usar solo si el primer intento falla | M |
| 5 | **Flujo agéntico con estado** (LangGraph): recuperar → juzgar suficiencia → reescribir y reintentar → generar, con límite de pasos. Estilo CRAG / Self-RAG | Reemplaza la abstención por scores (que no funciona) con una verificación explícita. Cumple "flujo con estado, reglas y límites" del §5.6 y da una pieza de arquitectura muy defendible | M |
| 6 | **Memoria conversacional** y reformulación con historial ("¿y el jefe de ese nivel?") | Hoy es de un solo turno. Es requisito de cualquier UI de chat | S–M |

### 4.2 Prioridad media (valor claro, más trabajo)

| # | Mejora | Notas | Esfuerzo |
| --- | --- | --- | :-: |
| 7 | **Extracción de entidades y relaciones a un grafo/tabla** (jefe, ítem, mazmorra, ubicación) con un LLM sobre el corpus; consulta con SQL o grafo (estilo GraphRAG-lite / LightRAG, pero sobre SQLite o NetworkX) | Resuelve los fallos de "lista todos los jefes de la Quest 1" (la lista está repartida en chunks) y preguntas de varios saltos. Extiende `query_game_facts`, que ya existe. También sirve de base para G3 (entidades de solución) | L |
| 8 | **Embeddings más fuertes**: `bge-m3` (denso + disperso + multi-vector, multilingüe), `Qwen3-Embedding` o `EmbeddingGemma`. Comparar contra e5-small con el mismo banco | e5-small es el modelo más chico posible. Además, un modelo multilingüe fuerte ayuda al español. Verificar tamaño y RAM (el objetivo es ≤ 2 GB) | S–M |
| 9 | **Reranker moderno** (`bge-reranker-v2-m3`, `Qwen3-Reranker`, o reranking con un LLM sobre los 10 candidatos) | El resultado negativo previo fue con MiniLM. Volver a probar con uno moderno es una buena ablación; úsalo solo si sube Recall@5 y no solo MRR. También como señal de confianza para la abstención | S–M |
| 10 | **Vector store con filtros nativos y búsqueda híbrida**: Qdrant (vectores densos + dispersos, filtros por payload para los gates) o LanceDB | Con ~700 chunks no se necesita por rendimiento. Se justifica solo por exponer los gates como filtros nativos y por tecnología. No lo haría al inicio | M |
| 11 | **Observabilidad**: Langfuse o Arize Phoenix (u OpenTelemetry) para trazas, tokens y costo | Complementa la traza propia. Útil para la demo ("diagnóstico de una falla real") | S |
| 12 | **Servidor MCP** que exponga `search_documents`, `query_game_facts`, `next_available_levels` | Barato (el pipeline ya está detrás de una API) y permite usar el sistema desde Claude Desktop u otros clientes. Muestra interoperabilidad | S |

### 4.3 Prioridad baja o con reservas

| Mejora | Por qué esperar |
| --- | --- |
| ColBERT / late interaction (PyLate, RAGatouille) | Buen resultado en general, pero con ~250 chunks la ganancia sobre híbrido + reranker será difícil de medir |
| Multimodal (mapas de Hyrule, capturas) con modelo de visión o ColPali | Atractivo para "dónde está X" (la ubicación está en mapas), pero el corpus es texto. Proyecto aparte |
| Fine-tuning de embeddings con pares sintéticos | Con 54 casos de evaluación no se podría validar sin sobreajustar |
| Compresión de contexto (LLMLingua) | El contexto es de 5 chunks; no hay problema de longitud |

### 4.4 Seguridad (hoy sin cubrir; pertenece a otro integrante pero pesa 15 pts)

Piezas de estado del arte que se pueden enchufar a los contratos existentes (`InputGuard`/`OutputGuard`) sin rediseñar:
- **Inyección de prompt:** Llama Prompt Guard 2 o un clasificador ligero, más *spotlighting* (delimitar el contexto como datos; `format_context` ya hace la mitad).
- **PII:** Microsoft Presidio en entrada y en auditoría.
- **Salida:** verificación de citas ya existe; agregar un chequeo de *groundedness* por oración con un juez.
- **Pruebas:** corpus adversario propio (inyección directa e indirecta incrustada en un chunk, evasión de spoiler, acción crítica sin confirmación, alucinación forzada), con el formato de 5 columnas que pide §10. Se puede complementar con Garak o promptfoo como referencia.

## 5. Interfaz: opciones

### 5.1 Requisitos previos (valen para cualquier opción)

1. **Streaming** (SSE) en la API: `POST /ask/stream`. Hoy `/ask` devuelve la respuesta completa.
2. **Estado de conversación** (historial por sesión) en la API, no en la UI.
3. **Un solo endpoint rico** que devuelva respuesta, citas, traza y bloqueos, para no llamar a `/search` aparte como hace hoy la UI.

### 5.2 Comparación

| Opción | Qué es | A favor | En contra | Encaje |
| --- | --- | --- | --- | --- |
| **NiceGUI** | UI en Python sobre Vue/Quasar, se monta dentro de FastAPI | Mismo proceso y lenguaje que la API; componentes ricos (tarjetas, chips, timeline, tablas, diálogos); websockets y streaming nativos; control total del diseño | Menos "chat listo" que Open WebUI; hay que diseñar | **Mejor para la UI propia del producto** |
| **Open WebUI** | Plataforma de chat completa (historial, usuarios, streaming, citas, modo oscuro) | Aspecto profesional de inmediato; se conecta vía API compatible con OpenAI o con *Pipelines/Functions* | Pesado (contenedor aparte); el selector de perfil, el progreso del jugador y el panel de trazas hay que forzarlos dentro de su modelo; revisar su licencia (tiene cláusula de marca) | Buena **segunda interfaz**, casi gratis si se agrega `/v1/chat/completions` |
| **Chainlit** | UI de chat para apps de LLM, con "pasos" desplegables | Muestra muy bien los pasos del RAG (reescritura, recuperación, filtros) y las citas | Proyecto mantenido por la comunidad desde 2025; menos flexible fuera del chat | Buena para depurar y mostrar la traza |
| **Gradio** | Demos rápidas de ML | Muy rápido de hacer; `ChatInterface` | Estética genérica; difícil salir del molde | Similar a lo que ya hay |
| **Streamlit** (actual) | Dashboards en Python | Ya funciona; cero costo | Se re-ejecuta el script en cada interacción; streaming y chat limitados | Dejar como panel de depuración |
| **Next.js + Vercel AI SDK / assistant-ui** | Front en React | Máxima calidad y control | Otro lenguaje y otro build; es la opción más costosa | Solo si alguien del equipo domina React |

### 5.3 Recomendación

- **UI principal: NiceGUI**, montada en la misma FastAPI (un proceso menos en `compose`).
- **Extra barato: endpoint compatible con OpenAI** (`/v1/chat/completions`, con el perfil y el juego en el modelo o en cabeceras), para poder enchufar Open WebUI y mostrar que el sistema es agnóstico al front.
- **Conservar Streamlit** como panel de depuración y de resultados de evaluación (o migrarlo al mismo NiceGUI).

### 5.4 Qué tendría la UI nueva

- Chat con streaming, historial y sugerencias de preguntas por juego.
- **Citas como chips** que abren el fragmento y el enlace a la wiki.
- **Indicadores de spoiler:** cuando se bloquea algo, un candado con el motivo y la opción de "ver de todos modos" (si la política lo permite).
- **Seguimiento de progreso:** para Zelda, mapa de las 9 mazmorras (hechas, disponibles, bloqueadas); para Ninja Gaiden, una línea de etapas. Con confirmación explícita al actualizar (`update_progress`).
- **Panel de traza**: variantes de consulta, candidatos con `blocked_by`, latencia por etapa, tokens y costo.
- **Panel de evaluación**: tabla de ablaciones y gráfico (línea base vs mejorada) leyendo `eval/results/`.
- Selector de juego y perfil; modo claro y oscuro; adaptable al celular.

## 6. Plan sugerido

Cada fase se evalúa con una ablación contra la anterior, como ya se hace.

| Fase | Contenido | Resultado esperado |
| --- | --- | --- |
| 0 (S) | Confirmar los 16 errores de test; diagrama formal §6; commit del estado | Base verde y entregable de arquitectura |
| 1 (M) | Haiku generator + salida estructurada + citas + abstención por el modelo + streaming | Sistema extremo a extremo |
| 2 (M) | Evaluación de generación y operación (fidelidad, citas, tokens, costo, P95) | Tabla línea base vs mejorada completa |
| 3 (M) | Contextual Retrieval y reescritura con LLM, comparados contra glosario y chunking actual | Recall@5 sobre NG y las tablas de ítems |
| 4 (M) | Flujo agéntico (LangGraph) con juicio de suficiencia y reintento; memoria conversacional | Abstención correcta y chat de varios turnos |
| 5 (M) | UI NiceGUI + endpoint OpenAI-compatible + panel de trazas y evaluación | Demo con calidad de producto |
| 6 (M–L) | Grafo/tabla de entidades; embeddings/reranker modernos; MCP; Langfuse | Material de "tecnologías nuevas" |
| 7 | Seguridad (con el integrante responsable), documento de 10–15 páginas, ensayo de la demo | Entrega |

Si el tiempo aprieta, el orden de recorte es: 6 → 5 (quedarse con Streamlit) → 4. **No recortar 1 y 2.**

## 7. Riesgos de la expansión

- **Alcance:** la regla del MVP del roadmap sigue siendo correcta; sumar tecnología sin medirla empeora la defensa. Cada pieza debe entrar con su ablación.
- **Sobreajuste al banco:** con 54 casos y glosarios escritos viendo los fallos, hay que ampliar el banco con preguntas nuevas de otras personas antes de afirmar mejoras (y reportar intervalos).
- **Costo y latencia:** reescritura con LLM, contexto por chunk y juez multiplican las llamadas. Hay que presupuestar tokens (la decisión sigue abierta en el roadmap) y cachear.
- **Dependencia de otros integrantes:** generación, gates y seguridad ya tienen dueño. Conviene acordar quién hace qué antes de tocar esas áreas.
- **Memoria:** el objetivo de ≤ 2 GB limita modelos de embeddings y rerankers grandes.

## 8. Decisiones que necesito de ti

1. ¿Quién está haciendo `HaikuGenerator` y en qué estado? Si no ha empezado, ¿lo hago yo (fase 1)?
2. ¿Las mejoras de RAG van a reemplazar la configuración servida o a convivir como alternativas seleccionables (recomendado, para poder hacer la ablación en vivo)?
3. ¿NiceGUI como UI principal, o prefieres Open WebUI como producto y Streamlit solo para depurar?
4. ¿Hay presupuesto de API para Contextual Retrieval, LLM-as-judge y reescritura con LLM?
5. ¿Se mantiene el alcance en inglés o entra el español en esta ronda (si es así, subir `bge-m3` en prioridad)?

---

*Nota sobre el estado del arte: los nombres de modelos y librerías de la sección 4 y 5 los conozco hasta mediados de 2026; antes de adoptar cualquiera conviene verificar versión, licencia y tamaño.*
