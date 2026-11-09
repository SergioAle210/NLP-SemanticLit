# Arquitecturas RAG, dónde estamos y cómo convertirlo en una contribución

Fecha: 2026-11-07. Complementa [informe-estado.md](informe-estado.md).

> **Cautela sobre las referencias.** Las citas de la sección 2 son de memoria (conocimiento hasta mediados de 2026), salvo las marcadas con enlace, que se verificaron con búsqueda web hoy. Antes de citar en un paper o documento hay que abrir cada una y confirmar autores, año y resultados.

## 1. Qué arquitectura tenemos hoy

Con la taxonomía de Gao et al. (2023), que separa RAG *naive*, *advanced* y *modular*:

| Etapa | Qué hace el proyecto hoy | Familia |
| --- | --- | --- |
| Pre-recuperación | Multi-consulta (ortografía + glosario), alias de ubicación, router de intención por reglas | Advanced / Modular |
| Recuperación | Híbrida BM25 + denso (e5-small), RRF plana, tokens de frase | Advanced |
| Post-recuperación | Filtros de acceso (G1 por juego), orden por RRF; reranker probado y descartado | Advanced |
| Herramientas | Text-to-SQL de solo lectura (`query_game_facts`), progreso del jugador | Modular (routing a herramientas) |
| Generación | **Extractiva, sin LLM** (Haiku pendiente) | — |
| Bucle de control | **Ninguno**: una pasada, un turno, sin verificar la evidencia | — |

**Diagnóstico:** es un *RAG avanzado modular, de una sola pasada, sin generación*. La parte diferenciadora ya existe, aunque a medias: el **control de acceso dependiente del progreso del jugador** (los "gates" anti-spoiler). Lo que falta para que sea arquitectura de estado del arte es el bucle de decisión (adaptativo / correctivo / agéntico) y la generación.

## 2. Mapa de arquitecturas RAG

### 2.1 Familias de la literatura

| Familia | Idea | Referencias clave | ¿Encaja aquí? |
| --- | --- | --- | --- |
| **RAG original** | Recuperar y concatenar al prompt | Lewis et al., 2020 (RAG) | Es la línea base |
| **Transformación de consulta** | Reescribir, descomponer o generar un documento hipotético antes de buscar | Rewrite-Retrieve-Read (Ma et al., 2023); HyDE (Gao et al., 2022); Step-back prompting (Zheng et al., 2023); RAG-Fusion | **Sí.** Reemplaza el glosario manual |
| **Indexación enriquecida** | Cambiar *qué* se indexa: contexto por chunk, proposiciones, resúmenes jerárquicos | Contextual Retrieval (Anthropic, 2024); Dense X / proposiciones (Chen et al., 2023); RAPTOR (Sarthi et al., 2024); Late chunking (Jina, 2024) | **Sí.** Ataca la dilución, el fallo dominante medido |
| **Recuperación neuronal avanzada** | Multi-vector, dispersos aprendidos | ColBERT / ColBERTv2; SPLADE; BGE-M3 | Parcial: `bge-m3` como ablación |
| **RAG adaptativo** | Un clasificador decide: sin recuperar, una pasada o varias | Adaptive-RAG (Jeong et al., 2024) | **Sí.** Evolución natural del router por reglas |
| **RAG correctivo / auto-reflexivo** | Juzgar la evidencia y corregir (reescribir, buscar de nuevo, descartar) | CRAG (Yan et al., 2024); Self-RAG (Asai et al., 2023) | **Sí.** Resuelve la abstención, que los scores no pueden decidir |
| **RAG iterativo / multi-salto** | Intercalar razonamiento y recuperación | IRCoT (Trivedi et al., 2022); FLARE (Jiang et al., 2023) | Para preguntas compuestas ("jefe del nivel 3 y cómo llegar") |
| **RAG sobre grafos** | Extraer entidades y relaciones; consultar el grafo | GraphRAG (Edge et al., 2024, Microsoft); LightRAG (Guo et al., 2024); HippoRAG (Gutiérrez et al., 2024) | **Sí, en versión ligera** (SQLite/NetworkX): listas y multi-salto |
| **RAG agéntico** | Uno o varios agentes planifican, usan herramientas y reflexionan | Survey de Singh et al. ([arXiv 2501.09136](https://arxiv.org/abs/2501.09136), taxonomía por cardinalidad, control, autonomía y representación del conocimiento); agentes de búsqueda entrenados con RL (Search-R1 y similares, 2025) | **Sí**, con límites estrictos (lo exige el §5.6 del curso) |
| **Contexto largo / CAG** | Meter todo el corpus en el contexto y cachearlo, sin recuperar | Cache-Augmented Generation (Chan et al., 2024) | **Obligatorio como línea base** (ver 3.3) |
| **RAG seguro / con permisos** | Control de acceso, defensa contra envenenamiento e inyección | Revisión [arXiv 2603.21654](https://arxiv.org/pdf/2603.21654); RBAC por filtrado de recuperación ([BRACIS](https://sol.sbc.org.br/index.php/bracis/article/view/40906)) | **Sí: es el núcleo diferenciador** |

### 2.2 Qué se usa en producción (patrones públicos)

Descripciones generales de lo que las empresas han documentado; no son especificaciones internas.

| Patrón | Dónde se ve | Lección para este proyecto |
| --- | --- | --- |
| Híbrido (léxico + denso) + reranker, en dos etapas | Buscadores empresariales y de IA (Elastic, Vespa, Cohere Rerank, Perplexity) | Ya hecho; falta un reranker moderno como ablación |
| Contextual Retrieval (contexto por chunk + BM25 + reranker) | Publicado por Anthropic | Mayor retorno esperado para el costo |
| **Recuperación con permisos (ACL-aware)** | Búsqueda empresarial (Glean, Microsoft 365 Copilot y similares) | La idea ya está en el proyecto; el filtro debe aplicarse **antes** de que el dato llegue al LLM |
| **Búsqueda agéntica sin índice vectorial** | Asistentes de código (grep/glob iterativo) | Un agente que usa búsqueda léxica con bucle puede igualar o superar al RAG vectorial en corpus pequeños |
| Investigación profunda (*deep research*) multiagente | Productos de OpenAI, Google, Anthropic | Excesivo aquí; sirve de referencia de arquitectura (planificador + subagentes + verificador de citas) |
| RAG + evaluación continua en CI + trazas | Práctica de ingeniería de LLMs | Ya tienen el banco; falta el juez de generación y el "gate" de regresión |

## 3. Lo que ya los diferencia y dónde está el hueco de investigación

### 3.1 Estado de la novedad (búsqueda de hoy)

- **No encontré** un artículo ni un producto que haga *RAG con control de acceso dependiente del progreso* para guías de videojuegos. Lo más cercano es un hilo anecdótico sobre chatbots de libros que filtran por capítulo ([Reddit](https://reddit.sentinel-team.org/posts/1rq8hu1/snapshots/2026-03-11T15%3A10%3A57.129045Z)), sin evaluación.
- **Benchmarks de RAG en videojuegos:** [ChronoPlay](https://liner.com/review/chronoplay-framework-for-modeling-dual-dynamics-and-authenticity-in-game) dice que faltaban benchmarks de RAG para juegos; trata la evolución temporal del contenido, no los spoilers.
- **Seguridad en RAG:** hay literatura de RBAC y de fugas ([revisión 2026](https://arxiv.org/pdf/2603.21654)) y buenas prácticas de industria, pero con permisos **estáticos** (rol → documentos). No encontré un tratamiento de permisos que **cambian con el estado del usuario**.

Esto es una búsqueda corta, no una revisión sistemática. Antes de afirmar novedad hay que hacer una búsqueda en Google Scholar, Semantic Scholar y ACL Anthology con términos como *spoiler*, *progress-aware retrieval*, *temporal knowledge gating*, *stateful access control RAG*.

### 3.2 Ideas de contribución, de más a menos defendible

**A. Benchmark y métricas de "RAG con permisos dependientes del estado" (recurso). La más realista.**
- Un conjunto de pruebas donde cada pregunta tiene respuesta correcta **distinta según el progreso** del jugador, con perfiles (inicial, medio, avanzado).
- Métricas nuevas: *Spoiler Leakage Rate* (fuga literal), fuga **parcial o inferida** (la respuesta no cita el spoiler pero lo insinúa), *Over-blocking Rate* (se bloquea lo permitido) y *Access-Control Tax* (cuánto baja el Recall@k por filtrar).
- El corpus es CC BY-SA 4.0 (StrategyWiki), así que **el dataset se puede publicar**. Esto es poco común y es lo que hace publicable un recurso.

**B. Dónde filtrar: pre-filtro vs post-filtro vs generación.**
- Comparar filtrar *antes* de la búsqueda (metadatos en el índice), *después* del top-k, y *solo en la salida* con un juez.
- Hipótesis medible: el post-filtro pierde recall porque el top-k se llena de contenido bloqueado (ya observado en el proyecto: Quest 2 tapando a Quest 1).
- Canales de fuga que casi nadie mide y que aquí son concretos: la **expansión de consulta**, los **chunks vecinos**, la **proximidad en el espacio de embeddings**, las **citas** y la **abstención** ("no puedo decirte eso" ya revela que existe algo).

**C. Robustez de recuperación híbrida ante perturbaciones triviales (resultado empírico propio).**
- Ya tienen un hallazgo reportable: quitar el "?" final cambiaba el ranking por la **fusión en dos niveles**; la fusión plana lo corrige. Más el hallazgo de que HNSW aproximado cambia resultados entre procesos. Es una nota corta o una sección de un paper más grande.

**D. RAG vs contexto largo con caché en corpus pequeños.**
- Cada juego cabe en una ventana de contexto (estimación: Zelda ≈ 243 chunks de ~225 palabras ≈ 55 mil palabras, unos 75 mil tokens; hay que medirlo). Pregunta: ¿cuándo gana RAG a CAG en calidad, costo y latencia, y qué pasa con los permisos?
- Con permisos por perfil el caché no se comparte entre perfiles: un punto fuerte a favor de RAG que se puede cuantificar.

**E. Resultados negativos documentados.** Reranker MiniLM, chunking por fila y reglas de identificadores empeoraron. Reportarlos con rigor tiene valor (los workshops los aceptan).

### 3.3 Cómo se vería la preguntas de investigación

1. **RQ1:** ¿Cuánto contenido restringido se filtra en un RAG con permisos dependientes del progreso, según dónde se aplique el control (índice, post-recuperación, salida) y por qué canales?
2. **RQ2:** ¿Cuál es el costo en recuperación (Access-Control Tax) de cada estrategia, y cómo lo reducen la indexación contextual y la reescritura de consulta?
3. **RQ3:** ¿En qué régimen (tamaño de corpus, número de perfiles) un RAG con filtros supera a un contexto largo cacheado?

## 4. Arquitectura objetivo propuesta

"**Progress-Aware Adaptive Hybrid RAG**": lo que ya hay, más tres bucles.

```text
Pregunta + perfil (juego, progreso)
  -> Guardrails de entrada (esquema, inyección, PII)
  -> Router adaptativo (clasificador, no reglas):
       sin recuperación | una pasada | multi-paso | herramienta (SQL / progreso)
  -> Transformación de consulta (LLM: reescritura/descomposición; glosario como respaldo)
  -> Recuperación híbrida con PRE-filtro de acceso en el índice
       (BM25 contextual + denso contextual; entidades/grafo ligero para listas)
  -> [reranker moderno, solo si mejora Recall@5]
  -> Evaluador de evidencia (CRAG): suficiente / reescribir y repetir (máx. N) / abstenerse
  -> Generación (Haiku, citas, esquema Answer)
  -> Verificador de salida: citas ⊆ contexto, groundedness, juez anti-spoiler
  -> Respuesta + traza (qué se bloqueó y por qué, tokens, costo)
```

Piezas por origen:

| Pieza | Origen | Estado |
| --- | --- | --- |
| Híbrido, RRF, alias, multi-consulta | Propio, ya medido | ✅ |
| Gates de acceso | Propio; G1 hecho, G2–G4 de otro integrante | 🟡 |
| Router adaptativo | Adaptive-RAG | ⬜ |
| Evaluador de evidencia / reintento | CRAG, Self-RAG | ⬜ |
| Indexación contextual | Contextual Retrieval | ⬜ |
| Grafo/tabla de entidades | GraphRAG-lite, LightRAG | ⬜ |
| Verificador anti-spoiler de salida | Propio (aporte) | ⬜ |

## 5. Plan de experimentos (cada fila es una ablación)

| # | Configuración | Qué responde |
| --- | --- | --- |
| E0 | Actual (híbrida + glosario, extractiva) | Línea base |
| E1 | + Haiku (una pasada) | Efecto de la generación |
| E2 | + Contextual Retrieval | ¿Baja la dilución? |
| E3 | + Reescritura LLM (sin glosario) | ¿Generaliza sin curar a mano? |
| E4 | + Evaluador de evidencia con reintento | Abstención y recall en preguntas difíciles |
| E5 | + Grafo de entidades para listas | Preguntas compuestas y de lista |
| E6 | Pre-filtro vs post-filtro vs solo salida | RQ1 y RQ2 |
| E7 | CAG (todo el juego en contexto, con caché) | RQ3 |
| E8 | Agente con búsqueda léxica iterativa (sin vectores) | ¿Hace falta el índice vectorial? |

**Condiciones para que sea ciencia y no demo:**
- Ampliar el banco con preguntas escritas por terceros y fijar un conjunto de **prueba ciego** que no se toque.
- Intervalos de confianza (bootstrap) y varias corridas por la varianza de los LLM.
- Anotar a mano la fuga (verdad de terreno) en una muestra y medir el acuerdo del juez LLM con esas etiquetas.
- Registrar tokens, costo y P95 en todas las filas.
- Liberar código, datos y semillas.

## 6. Dos usos distintos: paper vs portafolio de trabajo

| | Paper | Portafolio / entrevista |
| --- | --- | --- |
| Lo que importa | Una pregunta de investigación clara, resultados medidos con rigor | Un sistema completo, con decisiones razonadas y evidencia |
| Foco | RQ1–RQ3, benchmark, métricas de fuga | Arquitectura, evaluación en CI, costo/latencia, seguridad, trazas |
| Formato realista | Artículo de taller, o recurso/dataset en una conferencia de NLP/IR o de juegos (candidatos: workshops de ACL/EMNLP, SIGIR resource track, LREC, CHI Play, FDG; **verificar fechas y requisitos**) | Repositorio público + entrada de blog técnica + demo corta en video |
| Qué diferencia | El hueco en 3.1 | Los 13 ADR, las ablaciones con resultados negativos y la prueba de perturbación |

Ambos se alimentan del mismo trabajo: el benchmark (A) y las ablaciones E0–E8.

## 7. Recomendación de orden

1. **Haiku + evaluación de generación** (E1). Sin esto no hay sistema ni métricas de respuesta.
2. **Banco ampliado y métricas de fuga** (A). Es la base de todo lo demás, y el riesgo de sobreajuste lo exige.
3. **E2 y E3** (Contextual Retrieval y reescritura): ganancias de recuperación rápidas.
4. **E4** (evaluador de evidencia con reintento): da la parte "agéntica" defendible.
5. **E6 y E7**: las que sostienen la contribución.
6. Grafo, agente léxico y UI: según tiempo.

Esto ya se alinea con los gates G2–G4 y la seguridad, que tienen dueño en el equipo: la contribución depende de que esos gates **existan y sean medibles**, así que conviene coordinarlo ya.

## Fuentes consultadas hoy

- Singh et al., Agentic RAG survey: <https://arxiv.org/abs/2501.09136>
- Revisión de RAG seguro (2026): <https://arxiv.org/pdf/2603.21654>
- RBAC por filtrado en RAG (BRACIS): <https://sol.sbc.org.br/index.php/bracis/article/view/40906>
- ChronoPlay (benchmark RAG en juegos): <https://liner.com/review/chronoplay-framework-for-modeling-dual-dynamics-and-authenticity-in-game>
- Hilo sobre chatbot anti-spoiler para libros (anecdótico): <https://reddit.sentinel-team.org/posts/1rq8hu1/snapshots/2026-03-11T15%3A10%3A57.129045Z>
