# Hoja de ruta

Fases alineadas con el §7 de [course/instructions.md](course/instructions.md).

**Regla del MVP:** cada fase se suma sobre algo ya evaluado. Si el tiempo no alcanza, lo pendiente pasa a trabajo futuro sin romper lo anterior. El orden de prioridad es:
1. Zelda funcionando en inglés. ✅
2. Ninja Gaiden. ✅ (salvo G2b)
3. **Lo obligatorio del curso que falta:** G2 (spoilers por quest, la propuesta de valor), pruebas de seguridad del §10, generación con Haiku y su evaluación, y diagrama formal del §6.
4. Refinamientos (G3, G4, G2b).
5. Español.

| Fase | Entregable | Estado |
| --- | --- | --- |
| 1. Anteproyecto | Alcance, fuentes, arquitectura, riesgos, manifiesto | 🟡 Falta el diagrama formal del §6 (los manuales PDF se descartaron) |
| 2. Línea base (Zelda, inglés) | Ingesta → BM25 → `Answer`, servido por la API; 20 casos de Zelda | ✅ Con el generador extractivo · Haiku: otro integrante |
| 3a. Mejora (Zelda) | Chunking estructural, híbrida, multi-consulta, alias, G1, router y herramientas | ✅ Recuperación (0.94), router y herramientas · ⬜ G2 y G4 (otro integrante) · rerank y fichas descartados |
| 3b. Segundo juego | Ninja Gaiden: `linear_stage`, glosario, casos de NG, G2b | 🟡 Indexado, glosario y mini banco (0.92) ✅ · G2b ⬜ (otro integrante) |
| 3c. Refinamiento | G3 (entidades de solución) en ambos juegos | ⬜ Otro integrante |
| 3d. Español (opcional) | Traducción de la consulta + glosario + casos en español ([ADR-0001](architecture/decisions/0001-english-first.md)) | ⬜ Trabajo futuro (e5 multilingüe ya responde algunas preguntas en español) |
| 4. Evaluación | Benchmark, ablaciones, análisis de fallas ([evaluation/](evaluation/)) | 🟡 Recuperación ✅ (54 casos, ablaciones, perturbación) · generación ⬜ (con Haiku, otro integrante) |
| 5. Seguridad | Casos adversarios y reporte ([security/](security/)) | ⬜ Otro integrante |
| 6. Defensa | Documento de 10 a 15 páginas, demo y presentación de 15 min | ⬜ |

## Fase 2 en detalle

| Paso | Contenido | Estado |
| --- | --- | --- |
| 1 | Base del proyecto: uv, config por juego, contrato de salida, tests, CI | ✅ |
| 2 | Ingesta: limpieza, secciones, chunking fijo y metadatos ([ingestion/](ingestion/)) | ✅ |
| 3.1 | BM25, 20 casos de Zelda, evaluación de recuperación ([results.md](evaluation/results.md): Recall@5 0.78, MRR 0.47) | ✅ |
| 3.2 | Generación con Haiku: prompt con contexto cerrado, validación `Answer`, fallback extractivo | ⏸️ Otro integrante (contrato en [contracts/generation.md](contracts/generation.md)) |
| 3.3 | API mínima (`/ask`), SQLite (auditoría y perfiles de demo) | ✅ (fase 3a, paso 6) |
| 4 | Dockerfile y docker compose | ✅ (fase 3a, paso 6e) |

## Fase 3a en detalle

| Paso | Contenido | Estado |
| --- | --- | --- |
| 1 | Búsqueda semántica (embeddings + Chroma) y comparación de dos modelos | ✅ |
| 2 | Búsqueda híbrida RRF y comparación léxica / semántica / híbrida ([results.md](evaluation/results.md)) | ✅ |
| 3 | **Chunking estructural** por sección, con líneas completas y uniendo las secciones diminutas ([chunking.md](ingestion/chunking.md)) | ✅ |
| 4 | Reevaluación de 10 configuraciones; se elige **híbrida e5 + estructural**, con Recall@5 = 0.89 ([ADR-0009](architecture/decisions/0009-phase3-retrieval-config.md)) | ✅ |
| 5 | Contratos para el equipo: `Generator`, `AccessFilter`, `InputGuard`/`OutputGuard`, perfiles y pipeline con traza ([contracts/](contracts/README.md)). Se detectó y corrigió el bug de chunks con score 0 en BM25 | ✅ |
| 6 | API (FastAPI) sobre el pipeline, con SQLite para perfiles y auditoría ([api/](api/README.md)) | ✅ |
| 6c | Robustez: conjunto del equipo; reranker y chunking por fila (descartados); **multi-consulta con ortografía + glosario** ([ADR-0010](architecture/decisions/0010-query-expansion.md)); análisis de abstención | ✅ |
| 6d | 8 preguntas exploratorias (todas en el top-5); corrección con transposición de letras (Damerau); prueba de estrés de correcciones falsas ([results.md](evaluation/results.md)) | ✅ |
| 6b | Frontend mínimo (Streamlit) sobre la API ([ui/](ui/README.md)), verificado de punta a punta | ✅ |
| 6f | Fusión RRF plana (invariante al "?") y búsqueda semántica exacta: total 0.86 → **0.92**, equipo 0.75 → **0.88** ([ADR-0011](architecture/decisions/0011-flat-fusion-exact-dense.md)) | ✅ |
| 6e | Docker compose (`api` + `ui`, una imagen, 4 volúmenes), verificado de punta a punta ([deployment/](deployment/README.md)) | ✅ |
| 6g | **Router + herramientas (§5.6):** `query_game_facts` (SQL de solo lectura, tabla de jefes), `next_available_levels` y `update_progress` (con confirmación); casos del §8 en tests ([tools/](tools/README.md), [ADR-0013](architecture/decisions/0013-intent-router-and-tools.md)) | ✅ |
| 6h | Ninja Gaiden: mini banco (15 casos) y glosario; Recall@5 0.85 → **0.92** ([results.md](evaluation/results.md)). Limpieza de la "cuadrícula de fichas" corregida; "heal" falla por dilución | ✅ |
| 7 | Validar los glosarios con preguntas de otros integrantes (validación parcial en 6d); diccionario de inglés para reducir las correcciones falsas (4.9%) | ⬜ Opcional |
| 8 | Level ↔ Dungeon: alias de ubicación en el índice + tokens de frase; curso 0.89 → **0.94**, total → **0.94** ([ADR-0012](architecture/decisions/0012-location-aliases-phrase-tokens.md)) | ✅ |
| 8b | Ordinales en el mapa ("first dungeon" ↔ level 1); `exact_01` (rank 7). `team_08` "bombs" era un error de etiqueta (corregido: rank 1); mezcla de quests en "where is dungeon N?" → gate G2 ([results.md](evaluation/results.md)) | ⬜ |
| 9 | Segmentos de NG (para G2b) y chunking por fila solo para G3, si se necesita | ⬜ |

## Riesgos

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Curaduría más lenta de lo previsto | Alto | Zelda Q1 primero; Q2 solo en lo que difiere; NG, G3 y español en fases posteriores |
| Fuga de spoilers por páginas agregadas o escenas en la misma página | Alto | G2 (quest) primero; G2b y G3 con chunking por fila o por segmento **solo** en las páginas que lo necesiten (como estrategia global bajó el Recall@5); gates por fila en `query_game_facts`; guardrail de salida |
| Contaminación entre juegos | Medio | G1 en el pre-filtro y en la salida; casos multijuego |
| Línea base débil | Medio | Todo en inglés para aislar variables; trazas para diagnosticar |
| Integración tardía (Haiku, G2-G4, seguridad) | Alto | Contratos con implementaciones por defecto que ya funcionan; tests de contrato; volver a correr la evaluación completa al integrar |
| API de Claude no disponible | Medio | Fallback extractivo; caché en la evaluación |
| Red o SSL inestables al descargar | Bajo | Snapshot versionado; reintentos en el script |
| Alcance excesivo | Alto | Regla del MVP |

## Decisiones abiertas 🔶

- [x] Frontend mínimo: Streamlit ([ui/](ui/README.md)). El diseño definitivo lo decide otro integrante, contra la misma API.
- [x] Embeddings: `e5-small-multi` ([ADR-0009](architecture/decisions/0009-phase3-retrieval-config.md)).
- [x] Reranker: probado y descartado ([ADR-0010](architecture/decisions/0010-query-expansion.md)).
- [ ] Repo público o privado; renombrar el repo.
- [x] Repartir responsables.
- [ ] Presupuesto de tokens de la API key.
- [ ] Explicar al catedrático que Q1/Q2 + `revid` cubren el caso de "versión documental".
- [x] Manuales PDF: descartados (la wiki cubre el contenido; tienen copyright y no se redistribuyen).
- [x] Casos "sin respuesta" de Ninja Gaiden (2, en el mini banco).
