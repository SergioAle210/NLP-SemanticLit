# Memoria, caché de KV y otras técnicas avanzadas — qué usar en gamerag

Fecha: 2026-11-08. Estado de las fuentes: lo marcado **[verificado]** se leyó/buscó en esta sesión (enlaces al
final); lo marcado **[de memoria]** viene del conocimiento del modelo y hay que confirmarlo antes de citarlo en un
paper.

## 1. Qué dice el artículo de Anthropic [verificado]

["Components of agent memory"](https://www.anthropic.com/research/components-of-agent-memory) define la memoria de
agente como conocimiento que el agente gana con la experiencia y conserva entre sesiones (excluye cambios de
pesos, aprendizaje en contexto dentro de una conversación y compactación). Su jerarquía, de abajo a arriba:

1. **Transcripciones**: registro de eventos buscable (la base).
2. **Notas de memoria** que el agente escribe en un almacén (cada nota es una apuesta a que el patrón se repite).
3. **Representaciones** como wikis mantenidas por el agente (mapa navegable).
4. **Contexto inyectado** al iniciar cada sesión (capa pequeña; Claude Code carga solo ~200 líneas / 25 KB de su índice).

Mecanismo central: **"dreaming"** = pasada offline que revisa transcripciones y notas para corregir errores,
fusionar duplicados, construir wikis y promover notas clave al contexto inyectado. Resultados que reporta
(todos del propio artículo, no replicados aquí): en CL-Bench (tarea de base de datos) la memoria sube Opus 5.5 de
0.655 a 0.838; en un corpus de ~350 000 archivos, wiki + búsqueda llega a 61 % frente a 53 % solo con búsqueda y
ahorra ~20 000 tokens por pregunta; páginas por contrato con términos literales subieron de 72 % a 100 %.
Recomendaciones: decir al agente *para qué* sirve la memoria pero no *cómo* usarla (reglas rígidas dañan a los
modelos fuertes), mantener la capa inyectada pequeña, una página por agente para no pisarse, y enfocar el dreaming
en lo que cambia. Nota: el artículo **no** trata KV cache; eso es otra capa (sección 3).

## 2. Memoria aplicada a gamerag

gamerag no es un asistente de largo aliento, pero ya tiene tres de las cuatro capas y una cuarta es la más
valiosa para el proyecto:

| Capa del artículo | Equivalente hoy | Qué falta / propuesta |
|---|---|---|
| Memoria de trabajo | `QueryState` del grafo (`graph.py`) | ya existe; añadir sub-preguntas y resultados parciales |
| Transcripciones | `Trace` por consulta (log de auditoría) | persistir en SQLite y hacerlo buscable (hoy solo se devuelve) |
| Memoria de usuario | `Profile` + `update_progress` (con confirmación) | recordar preferencias (nivel de pista), preguntas ya resueltas, y **resumen de sesión** acotado por gates |
| Notas / wikis | glosario por juego (`config/games/*.yaml`) | **dreaming sobre trazas** (abajo) |

**Propuesta de contribución: "dreaming" sobre las trazas de fallo.** Un proceso offline revisa las trazas con
abstención o con evaluador "insuficiente" (ya guardamos `trace.evidence` con las reescrituras que ayudaron) y
propone entradas de glosario/alias (p. ej. "rhinoceros boss" → Dodongo) y páginas-resumen por entidad
(boss/ítem) que luego se indexan como chunks de nivel superior (parecido a RAPTOR [de memoria], pero dirigido por
fallos reales). Hay que **verificar contra la fuente** cada nota antes de promoverla (el artículo insiste en que las
notas pueden ser erróneas) y registrar su origen (traza + chunk), porque en este sistema una nota nueva también
debe heredar el **gate de spoilers** del contenido del que sale. Es el punto donde "memoria" y "acceso por
progreso" se cruzan, y es lo que ningún trabajo revisado combina (hipótesis a confirmar con búsqueda más amplia).

Riesgos específicos: una memoria compartida entre usuarios puede filtrar spoilers (una nota creada con la
sesión de un completista no puede mostrarse a un novato). Regla: toda nota hereda la etiqueta de acceso más
restrictiva de sus fuentes, y la memoria por usuario nunca cruza usuarios.

## 3. Caché de KV, prompt caching y contexto largo

| Técnica | Qué es | Aplica a gamerag |
|---|---|---|
| **Prompt caching** (API de Anthropic) | reutiliza el prefijo del prompt; lecturas a ~0.1× del precio de entrada | **Sí, barato**: poner instrucciones + definiciones fijas antes del contexto variable y marcar `cache_control`. Ahorro real solo si el prefijo supera el mínimo cacheable del modelo; hoy el prefijo es corto (~150 tokens), así que casi no rinde. Rinde con el modo "contexto largo" |
| **Prefix caching** (vLLM, SGLang) | reutiliza KV de prefijos en servidores propios | solo si se aloja un modelo propio; no con la API |
| **CacheBlend** [verificado] | reutiliza KV de chunks que no están al inicio, recalculando solo un subconjunto de tokens; reporta 2.2–3.3× menos TTFT | solo serving propio; útil como argumento de diseño, no para implementar |
| **CAG / contexto largo** [de memoria] | precargar todo el corpus en el contexto y cachearlo, sin recuperación | **Viable y es un baseline que hay que medir**: el corpus de Zelda 1 son 243 chunks (~27 000 palabras, unos 40 000 tokens); cabe en el contexto y, con prompt caching, cada pregunta repetida paga ~0.1× del prefijo |
| **Caché semántica de respuestas** | reusar respuestas de consultas parecidas | **Peligrosa aquí**: la respuesta depende del progreso. Debe tener como clave (juego, nivel de acceso, versión del índice); si no, filtra spoilers entre usuarios |

El `LLMClient` ya tiene una caché en disco **segura**: su clave es el hash de la solicitud completa (incluye el
contexto ya filtrado), así que dos perfiles con contextos distintos nunca comparten entrada.

**Experimento propuesto (RAG vs. CAG con gates):** con control de acceso, "contexto largo" obliga a armar un
contexto distinto por nivel de acceso (la caché se rompe por perfil), lo que cuantifica el **impuesto del control
de acceso** sobre CAG; es una pregunta de investigación concreta y barata de responder con este banco.

## 4. Otras técnicas de recuperación/generación relevantes

Prioridad según lo que mostró el banco difícil (sección 5). [de memoria] salvo donde se indica.

1. **Descomposición de consulta / ReAct acotado** (alta): los casos multi-salto son los únicos que fallan.
2. **Reranker cross-encoder** (media): ya existe como opción (`--reranker`); medirlo con el banco difícil.
3. **Contextual Retrieval** (media): prefijar cada chunk con su contexto antes de indexar; barato de hacer una vez
   (un costo de ingesta, no por consulta). Se puede construir con Haiku dentro del tope.
4. **Late interaction (ColBERT)** y **embeddings multi-vector** (baja): mejora léxico/semántico, pero el corpus es
   pequeño y el híbrido ya está saturado.
5. **GraphRAG / LightRAG** (baja-media): útil para relaciones jefe→mazmorra→ítem; el costo de construir el grafo es
   alto frente a un corpus de 243 chunks. Probar solo si se amplía el corpus.
6. **Self-RAG / críticos de fidelidad** (media): el nodo crítico del plan agéntico; falta medir fidelidad con un
   juez (hoy solo medimos citas y abstención).
7. **Evaluación**: RAGAS-style y **benchmarks por salto** como AgenticRAGTracer [verificado: ACL Findings 2026, 1 305
   ítems con preguntas intermedias por salto] para diagnosticar *en qué salto* falla el agente; LongMemEval
   (original y V2) [verificado] para la memoria. Cuidado: un estudio de junio de 2026 [verificado, vía buscador]
   encontró que la descomposición de consultas ayudó en un conjunto de DevOps pero empeoró la precisión en MuSiQue:
   los añadidos agénticos no son uniformemente buenos, hay que medirlos.

## 5. Banco difícil: primera lectura

`eval/cases_hard.jsonl` (21 casos de Zelda 1: multi-salto, inferencia numérica con dos páginas, identificadores
exactos, paráfrasis indirectas, errores de tipeo, premisas falsas y preguntas sin respuesta). Recuperador híbrido,
una corrida por configuración:

| Configuración | ctx_recall | ctx_coverage (multi-salto) | abstención | precisión de citas | costo/pregunta |
|---|---|---|---|---|---|
| extractivo | 1.00 | 0.917 | 0.857 | 0.36 | $0 |
| grafo + Haiku | 1.00 | 0.917 | 0.952 | 0.84 | $0.00022 |
| + evaluador si se abstiene | 1.00 | 0.917 | 0.952 | 0.84 | $0.00029 |
| + evaluador siempre | 1.00 | 0.917 | **1.00** | 0.77 | $0.00044 |

Lecturas honestas:
- **El corpus es demasiado pequeño y limpio para que la recuperación sea el cuello de botella**: el contexto
  contiene alguna evidencia en 21/21 casos incluso con paráfrasis y typos. Un banco más difícil exigiría más juegos
  o más páginas, no más preguntas sobre las mismas.
- **Lo que sí falla es el multi-salto**: `hard_01`, `hard_05` y `hard_11` entregan solo la mitad de la evidencia
  (`ctx_coverage` 0.5) en *todas* las configuraciones. El evaluador con una sola reescritura no lo arregla: hacen
  falta **dos búsquedas** (una por sub-pregunta). Es la evidencia para justificar el nodo de descomposición.
- El evaluador "siempre" corrige la abstención (premisas falsas) a costa de ~2× el costo; el condicional no.
- n = 21, una corrida: ninguna diferencia de un caso es concluyente.

## 6. Hoja de ruta sugerida

1. **Descomposición de consulta** como nodo del grafo (planner → N búsquedas → unión de contexto), medido con
   `ctx_coverage` en el banco difícil. Es el cambio con evidencia a favor.
2. **Baseline CAG** (corpus completo en contexto + prompt caching) contra el RAG actual, con y sin gates.
3. **Persistir trazas** y construir el **dreaming** sobre ellas (glosario/alias y resúmenes por entidad), heredando
   etiquetas de acceso.
4. Memoria de usuario acotada (preferencias, resumen de sesión) con las mismas reglas de acceso.
5. Juez de fidelidad (Haiku) y casos adversariales/de spoilers cuando estén los gates G2–G4.

## Fuentes

- [Components of agent memory (Anthropic)](https://www.anthropic.com/research/components-of-agent-memory)
- [CacheBlend (Microsoft Research)](https://www.microsoft.com/en-us/research/publication/you-only-prefill-once-combining-cached-knowledge-for-large-language-model-serving-with-cacheblend/) · [arXiv 2405.16444](https://arxiv.org/html/2405.16444v3)
- [LongMemEval-V2](https://arxiv.org/pdf/2605.12493) · [LongMemEval](https://arxiv.org/abs/2410.10813v2)
- [AgenticRAGTracer](https://arxiv.org/abs/2602.19127)
- [From Storage to Experience (survey de memoria de agentes)](https://arxiv.org/pdf/2605.06716) · [Anatomy of Agentic Memory](https://arxiv.org/html/2602.19320)
- [Fact, Fetch, and Reason (FRAMES)](https://arxiv.org/html/2409.12941v1)

---

## 7. Implementación y primeras mediciones (2026-11-08)

Implementado: trazas con `subqueries`/`cited` persistidas en la tabla `audit` (con PII redactada también en las
sub-consultas y reescrituras); `agents/planner.py` + nodo `plan` del grafo (varias recuperaciones y unión de
contextos); `gamerag/dream.py` (notas verificadas); `guardrails/provenance.py` (acceso de las notas) y carga de
notas con `GAMERAG_MEMORY_NOTES`. Activación: `GAMERAG_USE_GRAPH`, `GAMERAG_PLANNER`, `GAMERAG_MEMORY_NOTES`.
Evaluación: `python -m gamerag.evaluation.e2e --planner --notes --split train|test --trace-db ...`.

Cómo se garantiza el acceso de las notas: una nota se muestra a un perfil solo si **todas** sus fuentes pasan
**todos** los demás filtros (`ProvenanceFilter`); una fuente desconocida bloquea la nota. Funciona con G2–G4 sin
tocarla. Se prueba con un gate de nivel de ejemplo (14 tests en `tests/test_memory.py`); con la implementación
actual (solo G1) la métrica de fuga en la corrida real es trivialmente 0, así que la garantía real descansa en esos
tests hasta que existan los gates.

Banco difícil (21 casos, híbrido, Haiku; partición estable por hash: 9 train / 12 test; una corrida cada una):

| Prueba | Resultado |
|---|---|
| Planner, test | descompone 4/12; `ctx_coverage` 0.909 → 0.909 (sin cambio); 1 caso más se abstiene (abstención 1.00 → 0.92) |
| Planner + evaluador, train | `hard_01` pasa de cobertura 0.5 a 1.0 (descompuesto en "qué ítem muestra el Triforce" + "cuántas piezas"); 9/9 con evidencia completa |
| Dreaming sobre train | 9 trazas → 1 candidata multi-salto → **1 nota aceptada** (compás + piezas del Triforce, verificada contra sus 2 fuentes) |
| Réplica de train con la nota, **sin** planner | `hard_01`: cobertura 0.5 → **1.0** y la nota aparece en el contexto (control sin nota: 0.5) |
| Transferencia a test con la nota | sin efecto (1 nota; los casos de test son otros temas) |
| Perfil novato con planner + notas, 21 casos | 0 fugas de notas (trivial con solo G1) |
| Banco principal (54), planner | contexto 0.959 (igual que sin planner), abstención 0.926 (igual), descompone 7 % de las preguntas, costo $0.00032 vs $0.00026 |

**Lectura honesta.**
1. La **descomposición** arregla el multi-salto explícito (`hard_01`) pero no el implícito ni el de vocabulario
   distinto: `hard_11` se descompone bien y la 2.ª sub-pregunta ("qué necesito para derrotar a Ganon") sigue sin
   recuperar la Silver Arrow; `hard_05` ("¿cuántos golpes de espada de madera?") necesita saber que HP = golpes de
   espada de madera, algo que el planner no ve como un salto. Son exactamente los huecos que una nota de
   conocimiento (definición de HP, página de entidad "Ganon") cubriría.
2. El **dreaming funciona como mecanismo** (la nota verificada convierte 2 saltos en 1 búsqueda y evita llamar al
   planner), pero con 9 trazas solo produce 1 nota: **no se puede afirmar transferencia**. Hace falta un volumen de
   trazas (decenas o cientos de preguntas reales) y casos de test que compartan entidades con los de entrenamiento.
3. El verificador es deliberadamente estricto (rechazó una primera versión por mencionar "NES" y "pieces" que no
   estaban en las fuentes); se relajó solo para el título.
4. n pequeño, una corrida, y Haiku no es determinista: tratar todo como evidencia de funcionamiento, no de mejora.

---

## 8. Notas del dreaming: comparación pareada con más métricas (2026-11-08)

`ctx_recall` (¿el contexto contiene *alguna* evidencia?) está saturado (0.94–0.96), así que no discrimina. Se comparó
la misma configuración (híbrido + Haiku + planner) **sin notas vs. con 24 notas** (20 de Zelda y 4 de Ninja Gaiden,
generadas de 90 preguntas sintéticas ajenas a los bancos) con `python -m gamerag.evaluation.compare`, que añade un
juez LLM de corrección (correcto 1 / parcial 0.5 / incorrecto 0), la posición del primer chunk relevante
(`ctx_mrr`), la cobertura multi-salto, citas, tokens, costo y latencia.

| Banco | Métrica | Sin notas | Con notas | Solo casos donde se usó una nota |
|---|---|---|---|---|
| Difícil (21; notas en 8) | corrección (juez) | 0.833 | **0.857** | 0.813 → 0.875 |
| | `ctx_mrr` | 0.858 | 0.796 | 0.838 → 0.698 |
| | precisión de citas | 0.816 | 0.796 | 0.771 → 0.729 |
| Principal (54; notas en 13) | corrección (juez) | 0.833 | 0.824 | 0.923 → 0.846 |
| | `ctx_mrr` | 0.671 | 0.657 | 0.731 → 0.673 |
| | precisión de citas | 0.763 | 0.729 | 0.853 → 0.756 |
| | tokens de entrada / pregunta | 2331 | 2364 (+1.4 %) | 2479 → 2659 |
| | cobertura multi-salto | 0.949 | 0.949 | sin cambio |

**Lectura.**
- **Corrección de la respuesta:** sin cambio medible. Banco difícil: +1 caso (`hard_10`); banco principal: 3 casos
  mejoran y 4 empeoran. Dos de esos 4 (`zelda_extra_01/02`) **no tenían ninguna nota en el contexto**, es decir, la
  diferencia es variación de Haiku entre corridas: el ruido de referencia es de ±2 casos por 54, mayor que cualquier
  efecto de las notas.
- **Ranking y citas:** peores con notas (−1 a −6 pts de `ctx_mrr`, −2 a −10 pts de precisión de citas en los casos
  afectados). Las notas ocupan el primer lugar en 3 de 13 casos donde aparecen y desplazan al chunk original.
  Parte del efecto es de la métrica (la relevancia se define por evidencia *literal* y las notas parafrasean), pero
  `zelda_compound_02` muestra un daño real: dos notas en el contexto llevaron al generador a decir que los documentos
  "no identifican claramente" al jefe del Level 1.
- **Costo/latencia:** +1.4 % de tokens, costo igual, latencia sin diferencia consistente.
- **Conclusión:** con 24 notas de un corpus de 327 chunks, la memoria **no aporta mejora medible y puede estorbar al
  ranking**. No es evidencia en contra del enfoque: el corpus es demasiado pequeño para que haya relaciones
  multi-salto que consolidar (solo 24 notas de 90 preguntas) y las notas compiten con chunks que ya tienen la
  evidencia. Hipótesis a probar con el corpus ampliado: (1) indexar las notas con menor peso o solo como
  alias de recuperación en lugar de chunks citables, (2) medir sobre preguntas multi-salto reales, no sintéticas.
