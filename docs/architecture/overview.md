# Arquitectura

Cubre el §6 de [course/instructions.md](../course/instructions.md). El diagrama formal está pendiente (ver la [hoja de ruta](../roadmap.md)).

## Componentes

| Componente | Paquete / archivo | Responsabilidad | Estado |
| --- | --- | --- | --- |
| Configuración global | `src/gamerag/settings.py` | Variables de entorno y `.env`, rutas | ✅ |
| Configuración por juego | `config/games/*.yaml`, `src/gamerag/games.py` | Modelo de progreso, ubicación, herramientas ([ADR-0007](decisions/0007-per-game-config.md)) | ✅ |
| Contrato de salida | `src/gamerag/schemas.py` | Respuesta validada con Pydantic (§11) | ✅ |
| Ingesta | `src/gamerag/ingest/` | Wikitext → chunks con metadatos ([ingestion/](../ingestion/)) | ✅ |
| Recuperación | `src/gamerag/retrieval/` | BM25, semántica (Chroma) e híbrida RRF con multi-consulta ([retrieval/](../retrieval/README.md)); reranker probado y descartado | ✅ |
| Evaluación | `src/gamerag/evaluation/` | Banco de pruebas, métricas, ejecución ([evaluation/](../evaluation/)) | ✅ Recuperación |
| Generación | `src/gamerag/generation/` | Contrato `Generator`; extractivo y fallback ([contracts/generation.md](../contracts/generation.md)) | 🟡 Falta Haiku |
| Herramientas | `src/gamerag/tools/` | Router por reglas; `query_game_facts`, `next_available_levels`, `update_progress` ([tools/](../tools/README.md)) | ✅ |
| Guardrails | `src/gamerag/guardrails/` | Contratos `InputGuard`, `AccessFilter`, `OutputGuard`; G1 y citas ([contracts/access-and-guardrails.md](../contracts/access-and-guardrails.md)) | 🟡 Faltan G2-G4, inyección, PII |
| Progreso | `src/gamerag/progress/` | `Profile` con progreso `level_set` / `linear_stage`; perfiles sembrados | ✅ |
| Pipeline | `src/gamerag/pipeline.py` | Une los contratos y produce la `Trace` auditable ([contracts/pipeline.md](../contracts/pipeline.md)) | ✅ |
| API | `src/gamerag/api.py`, `src/gamerag/store.py` | FastAPI: backend único que usan la interfaz y el benchmark; SQLite con perfiles y auditoría ([api/](../api/README.md)) | ✅ |
| UI | `src/gamerag/ui/` | Streamlit: solo presentación, consume la API ([ui/](../ui/README.md)) | ✅ Mínima |
| Despliegue | `Dockerfile`, `compose.yaml` | `api` + `ui`, volúmenes ([deployment/](../deployment/README.md)) | ✅ |

## Stack

| Capa | Elección | Motivo |
| --- | --- | --- |
| Entorno | uv (`pyproject.toml` + `uv.lock`) | Instalación reproducible; Docker con caché |
| API | FastAPI | Pydantic nativo, que es el contrato de salida |
| UI | Streamlit (interfaz mínima) | Todo en Python; suficiente para la demo. El diseño definitivo puede usar otra tecnología contra la misma API |
| Parser de wikitext | mwparserfromhell | Plantillas anidadas ([ADR-0005](decisions/0005-wikitext-cleaning.md)) |
| Índice léxico | rank-bm25 | Línea base; suficiente para unos 1k chunks |
| Índice vectorial | ChromaDB embebido | Sin servidor; filtros `where` para los gates |
| Embeddings | `multilingual-e5-small` | Mejor Recall@5 en la híbrida con chunking estructural ([ADR-0009](decisions/0009-phase3-retrieval-config.md)) |
| Reranker | Descartado | Recall@5 0.89 → 0.78 y unas 40 veces más lento ([ADR-0010](decisions/0010-query-expansion.md)) |
| LLM | Claude Haiku | Generación; bajo costo. El router es por reglas ([ADR-0013](decisions/0013-intent-router-and-tools.md)) |
| Estado | SQLite en el volumen `state/` | Perfiles, progreso y auditoría ([ADR-0004](decisions/0004-sqlite-and-demo-profiles.md)) |
| Contenedores | docker compose: `api` + `ui` | torch solo CPU; volúmenes para modelos, índice, chunks y estado ([deployment/](../deployment/README.md)) |

**Recursos objetivo del backend:** 2 GB de RAM o menos. Lo pesado son torch y los modelos, no el corpus ni SQLite. El reranker se descartó, así que no ocupa memoria.

## Fases del RAG y estado actual

Un RAG tiene dos momentos. En la **indexación** (offline, una vez) se preparan los documentos. En la **consulta** (cada pregunta) se recuperan los fragmentos relevantes (*Retrieval*), se arma un prompt con ellos (*Augmentation*) y el LLM redacta la respuesta citándolos (*Generation*).

```mermaid
flowchart LR
    subgraph IDX["A. Indexación (offline)"]
        direction TB
        S["Snapshot de la wiki<br/>(CC BY-SA, revid)"] --> CL["Limpieza<br/>clean.py"]
        CL --> SE["Secciones<br/>sections.py"]
        SE --> CH["Chunking<br/>chunking.py"]
        CH --> MD["Metadatos<br/>location.py"]
        MD --> J[("chunks.jsonl")]
        J --> IL["Índice léxico<br/>BM25"]
        J --> IV[("Índice vectorial<br/>Chroma")]
    end

    subgraph QRY["B. Consulta (cada pregunta)"]
        direction TB
        Q["Pregunta"] --> R["R · Retrieval<br/>top-k fragmentos"]
        R --> A["A · Augmentation<br/>prompt = instrucciones +<br/>fragmentos + pregunta"]
        A --> G["G · Generation<br/>LLM con citas<br/>o abstención"]
        G --> ANS["Respuesta validada<br/>(Answer)"]
    end

    IL --> R
    IV -.-> R
    EV["Evaluación de recuperación<br/>Recall@k · MRR"] -.->|mide| R

    classDef done fill:#d4edda,stroke:#28a745,color:#155724
    classDef pending fill:#f8f9fa,stroke:#adb5bd,color:#6c757d,stroke-dasharray: 5 5
    class S,CL,SE,CH,MD,J,IL,IV,Q,R,EV done
    class A,G,ANS pending
```

En verde lo implementado y en gris punteado lo pendiente: la *Augmentation* y la *Generation* (paso 3.2, que requiere la API key). Hoy, una pregunta devuelve los fragmentos recuperados (léxica, semántica o híbrida), pero todavía no una respuesta redactada.

## Flujo de consulta

```text
UI (juego, perfil, progreso del juego activo, pregunta)
  -> Guardrails de entrada (esquema, longitud, inyección, PII)
  -> Router de intención por reglas (herramientas habilitadas según la config del juego)
       ├─ pregunta del juego    -> multi-consulta -> búsqueda híbrida -> gates (AccessFilter) -> contexto
       ├─ lista de jefes        -> query_game_facts (SQL de solo lectura; gates por fila)
       ├─ "what should I do next?" -> next_available_levels (solo Zelda: no lineal)
       └─ "I just beat level N" -> update_progress (no se ejecuta: needs_human_review)
       (si la herramienta falla -> búsqueda; sin evidencia suficiente -> abstención del generador)
  -> Generación (Haiku, contexto cerrado, citas obligatorias)
  -> Guardrails de salida (Pydantic, citas ⊆ permitidas, entidades bloqueadas, juego correcto)
  -> Respuesta + traza de auditoría (SQLite)
```

**Estado de cada paso:**
- **Implementados:** el router, las herramientas, la multi-consulta, la búsqueda híbrida, el gate G1 (por juego), la validación de citas y del juego, y la traza.
- **Con implementación por defecto, a cargo de otros integrantes:**
  - generación con Haiku (hoy, generador extractivo);
  - detección de inyección y PII en la entrada (hoy, validación de esquema y longitud);
  - gates G2 a G4 y entidades bloqueadas.

  Los contratos están en [contracts/](../contracts/README.md).

## Flujo de ingesta

```text
Snapshot de la wiki (repo) -> limpieza -> secciones -> chunking -> metadatos -> JSONL -> índices
```

El detalle está en [ingestion/](../ingestion/).

## Línea base y versión mejorada

| | Línea base (fase 2) | Mejorada (fase 3) |
| --- | --- | --- |
| Chunking | Fijo: 225 palabras, solapamiento de 30 | Estructural por sección |
| Recuperación | BM25, top-5 | Híbrida (BM25 + e5, RRF plana) + multi-consulta (ortografía, glosario) + alias de ubicación y tokens de frase. Rerank probado y descartado |
| Gates | Ninguno, a propósito | G1 implementado; G2 a G4 a cargo de otro integrante ([access-control.md](access-control.md)) |
| Router y herramientas | No | Sí, router por reglas ([ADR-0013](decisions/0013-intent-router-and-tools.md)) |
| Recall@5 en Zelda (curso, 18 casos) | 0.78 | 0.94 |

La línea base no tiene gates para poder **medir** cuánto spoiler y cuánta mezcla entre juegos y quests se produce sin control.

## Herramientas

| Herramienta | Juegos | Justificación | Límites |
| --- | --- | --- | --- |
| `search_documents` | Ambos | Texto no estructurado | top-k ≤ 10; gates obligatorios |
| `query_game_facts` | Zelda (tabla de jefes; NG no tiene tabla equivalente) | Listas completas que el RAG devuelve partidas | Solo lectura, consultas predefinidas parametrizadas, máximo 50 filas, gates por fila |
| `next_available_levels` | Solo Zelda | Depende del perfil, no de la wiki | Solo números de nivel, no cómo resolverlos; la config lo impide en NG |
| `update_progress` | Ambos | Cambiar el progreso cambia qué contenido se ve: es una acción crítica | No se ejecuta: `needs_human_review` |

Detalle en [tools/README.md](../tools/README.md).
