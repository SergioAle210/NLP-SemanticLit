# Resultados

Registro de cada corrida relevante. El detalle completo de cada una, con los candidatos por caso y su score y relevancia, está en `eval/results/`.

## Recuperación: línea base (2026-11-05)

**Configuración:** Zelda · BM25 (`k1 = 1.5`, `b = 0.75`) · chunking `fixed-w225-o30` (153 chunks) · sin gates · 18 casos con respuesta.

Comando: `uv run python -m gamerag.evaluation.retrieval zelda1`. Archivo: `eval/results/2026-11-05_zelda1_bm25-fixed.json`.

| Métrica | Valor | Meta |
| --- | ---: | ---: |
| Recall@1 | 0.33 | — |
| Recall@3 | 0.56 | — |
| **Recall@5** | **0.78** | ≥ 0.80 |
| **MRR** | **0.47** | — |
| Coverage@5 | 0.78 | — |

| Categoría | n | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| Directas | 5 | 0.80 | 0.65 |
| Paráfrasis | 3 | 0.67 | 0.42 |
| Identificadores exactos | 3 | 0.67 | 0.46 |
| Compuestas | 3 | 0.67 | 0.28 |
| Ambiguas | 2 | 1.00 | 0.67 |
| Versión | 2 | 1.00 | 0.23 |

### Diagnóstico de fallos

Se siguió el orden de diagnóstico del curso (tema 08): primero confirmar que existe un chunk con la evidencia (un test lo garantiza para todos los casos) y después ver dónde quedó en el ranking.

| Caso | Rank del primer relevante | Causa | Mejora candidata |
| --- | ---: | --- | --- |
| `direct_04` "item in Level-3 of the first quest" | > 20 | **Desajuste de identificadores:** el usuario dice *Level-3* y *first quest*; la página se titula *Dungeon 3* y *Quest 1*. Los chunks del Walkthrough mencionan todos los niveles y dominan | Normalizar la consulta con alias del dominio (level ↔ dungeon, first ↔ 1st ↔ 1); búsqueda semántica |
| `compound_03` "enter Level-4 in the first quest…" | > 20 | Ídem | Ídem |
| `exact_01` "old man in Level-4 of the first quest" | 19 | Ídem; además, el chunk con la frase está en medio del recorrido de la mazmorra | Ídem + chunking estructural |
| `paraphrase_01` "sail across the sea" | > 20 | **Paráfrasis pura:** ninguna palabra en común con "cross lakes and oceans" | Búsqueda semántica (fase 3) |
| `direct_01` "Which button swings the sword?" (acierto en rank 4) | 4 | **Sin stemming:** "swings" ≠ "swing" | Stemming o búsqueda semántica |

**Mezcla de versiones (casos `version_*`):** aciertan en el top-5 (Recall@5 = 1.0), pero con MRR = 0.23. A la pregunta *"In the first quest, which dungeon has the Ladder?"*, el **top-1 es una mazmorra de la Second Quest** (`underworld-quest-2-dungeon-7`), y el ranking de las dos preguntas (first y second) es casi idéntico. Es la evidencia de que hace falta el filtro de quest (gate G2, [access-control.md](../architecture/access-control.md)).

### Hipótesis para la fase 3

1. La búsqueda semántica debería recuperar `paraphrase_01` y mejorar `direct_01`.
2. Un alias de identificadores en la config del juego (level ↔ dungeon, first ↔ 1) debería recuperar `direct_04`, `compound_03` y `exact_01`.
3. El filtro de quest debería llevar los casos de versión a MRR ≈ 1.
4. El chunking estructural debería mejorar el MRR de las compuestas.

Cada una se mide por separado (ablación).
