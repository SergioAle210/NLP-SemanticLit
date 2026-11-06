# Hoja de ruta

Fases alineadas con el §7 de [course/instructions.md](course/instructions.md).

**Regla del MVP:** cada fase se suma sobre algo ya evaluado. Si el tiempo no alcanza, lo pendiente pasa a trabajo futuro sin romper lo anterior. El orden de prioridad es:
1. Zelda funcionando en inglés.
2. Ninja Gaiden.
3. Refinamientos (G3).
4. Español.

| Fase | Entregable | Estado |
| --- | --- | --- |
| 1. Anteproyecto | Alcance, fuentes, arquitectura, riesgos, manifiesto | 🟡 Falta revisar los PDF y hacer el diagrama formal |
| 2. Línea base (Zelda, inglés) | Ingesta → BM25 → Haiku → `Answer`, servido por la API; 20 casos de Zelda | 🟡 En curso |
| 3a. Mejora (Zelda) | Chunking estructural, híbrida, rerank, G1, G2 y G4, router, herramientas, fichas y pistas | 🟡 En curso |
| 3b. Segundo juego | Ninja Gaiden: `linear_stage`, G2b, fichas por acto, casos de NG y multijuego | ⬜ |
| 3c. Refinamiento | G3 (entidades de solución) en ambos juegos | ⬜ |
| 3d. Español (opcional) | Traducción de la consulta + glosario + casos en español ([ADR-0001](architecture/decisions/0001-english-first.md)) | ⬜ |
| 4. Evaluación | Benchmark, ablaciones, análisis de fallas ([evaluation/](evaluation/)) | ⬜ |
| 5. Seguridad | Casos adversarios y reporte ([security/](security/)) | ⬜ |
| 6. Defensa | Documento de 10 a 15 páginas, demo y presentación de 15 min | ⬜ |

## Fase 2 en detalle

| Paso | Contenido | Estado |
| --- | --- | --- |
| 1 | Base del proyecto: uv, config por juego, contrato de salida, tests, CI | ✅ |
| 2 | Ingesta: limpieza, secciones, chunking fijo y metadatos ([ingestion/](ingestion/)) | ✅ |
| 3.1 | BM25, 20 casos de Zelda, evaluación de recuperación ([results.md](evaluation/results.md): Recall@5 0.78, MRR 0.47) | ✅ |
| 3.2 | Generación con Haiku: prompt con contexto cerrado, validación `Answer`, fallback extractivo | ⏸️ Requiere la API key |
| 3.3 | API mínima (`/ask`), SQLite (auditoría y perfiles de demo) | ⬜ |
| 4 | Dockerfile y docker compose | ⬜ |

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
| 6b | Frontend mínimo (Streamlit) + Docker compose | ⬜ Siguiente |
| 7 | Validar el glosario con una segunda tanda de preguntas del equipo; glosario de Ninja Gaiden | ⬜ |
| 8 | Level ↔ Dungeon: las reglas de reescritura empeoraron; alternativa pendiente (p. ej. metadatos de ubicación en la consulta) | ⬜ |
| 9 | Segmentos de NG (para G2b) y chunking por fila solo para G3, si se necesita | ⬜ |

## Riesgos

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Curaduría más lenta de lo previsto | Alto | Zelda Q1 primero; Q2 solo en lo que difiere; NG, G3 y español en fases posteriores |
| Fuga de spoilers por páginas agregadas o escenas en la misma página | Alto | Chunking por fila y por segmento, G2b, G3, guardrail de salida y casos específicos |
| Contaminación entre juegos | Medio | G1 en el pre-filtro y en la salida; casos multijuego |
| Línea base débil | Medio | Todo en inglés para aislar variables; trazas para diagnosticar |
| OCR de los manuales | Medio | El manual es secundario |
| API de Claude no disponible | Medio | Fallback extractivo; caché en la evaluación |
| Red o SSL inestables al descargar | Bajo | Snapshot versionado; reintentos en el script |
| Alcance excesivo | Alto | Regla del MVP |

## Decisiones abiertas 🔶

- [ ] Frontend: Streamlit o HTMX.
- [x] Embeddings: `e5-small-multi` ([ADR-0009](architecture/decisions/0009-phase3-retrieval-config.md)).
- [ ] Reranker: modelo por elegir (fase 3a, paso 8).
- [ ] Repo público o privado; renombrar el repo.
- [ ] Repartir responsables.
- [ ] Presupuesto de tokens de la API key.
- [ ] Explicar al catedrático que Q1/Q2 + `revid` cubren el caso de "versión documental".
- [ ] Revisar los manuales: si tienen texto, qué incluyen (para el criterio de premisa) y si requieren OCR.
- [ ] Caso "sin respuesta" de Ninja Gaiden.
