# ADR-0011: Fusión RRF plana en la multi-consulta y búsqueda semántica exacta

**Estado:** aceptado (2026-11-06). Modifica cómo se fusionan las listas del [ADR-0010](0010-query-expansion.md); el resto de ese ADR se mantiene.

## Contexto

- **Al probar la interfaz,** "How do i attack" (sin "?") dejaba Controls en el **rank 8**. Con "?", quedaba en el **rank 1**.
- **Causa:** la fusión era en dos niveles. Primero se hacía RRF de BM25 + e5 por cada variante y después RRF entre variantes.
  - Con la variante ("… swing the sword A button"), los dos recuperadores ponían Controls en el rank 1, pero al fusionarse esa lista contaba como **un solo voto**.
  - Los resultados mediocres de la pregunta original, que aparecían en las dos listas, sumaban más.
  - El "?" movía el embedding de la original lo justo para cambiar el resultado.
- **Prueba de perturbación** (el banco quitando el "?" final): el total bajaba de 0.86 a 0.81. Dos casos se caían del top-5.
- **Al medir apareció un segundo problema:** una evaluación dio 0.89 y las siguientes 0.92 con el mismo código. Chroma usa HNSW, que es **aproximado**: en 1 de 3 procesos, el top-20 de una consulta no coincidía con el top-20 exacto.

## Decisión

1. **Fusión plana:** cuando hay variante, se hace un solo RRF sobre las 4 listas (BM25 y e5 × original y variante). Cada lista vota por separado, así que el acuerdo entre recuperadores sobre la variante se conserva.
2. **Búsqueda semántica exacta:** se piden a Chroma todos los chunks del juego (respetando `where`) y se ordenan por coseno exacto. Chroma sigue siendo el almacén persistente y el filtro de metadatos.

Ninguna de las dos decisiones agrega parámetros: no hay nada que ajustar contra el banco. El criterio para elegir la fusión se fijó antes de medir: no perder en las preguntas del curso y reducir la diferencia entre la pregunta con "?" y sin "?".

## Resultados (con búsqueda exacta)

| Fusión | Pregunta | Curso (18) | Equipo (8) | Total (36) | MRR |
| --- | --- | ---: | ---: | ---: | ---: |
| Sin expansión | tal cual / sin "?" | 0.89 / 0.89 | 0.50 / 0.50 | 0.72 / 0.72 | 0.44 |
| En dos niveles (ADR-0010) | tal cual / sin "?" | 0.89 / 0.89 | 0.75 / 0.75 | 0.86 / **0.81** | 0.49 |
| **Plana** | tal cual / sin "?" | 0.89 / 0.89 | **0.88 / 0.88** | **0.92 / 0.92** | **0.56** |

- **Casos que mejoran:**
  - `team_02` "how can i heal?" (rank 9 → 3);
  - `robust_06` "secondary item" (11 → 5);
  - `team_01`, `robust_01` y `robust_03` suben al rank 1.
- **Casos que bajan sin salir del top-5:** `robust_02` (2 → 3) y `team_04` (2 → 4).
- **Fuera del banco** (11 preguntas exploratorias, con y sin "?"): con la fusión plana, las **22 de 22** quedan en el top-5; con la de dos niveles, 20 de 22. Algunas bajan algo dentro del top-5: "booomerang" pasa del rank 1 al 2-3 y "heal" del 1 al 2.
- **Los números anteriores no cambian con la búsqueda exacta.** El 0.89 de aquella corrida fue un caso aislado de HNSW.
- **Latencia media:** de 29 a 44 ms.

## Alternativas consideradas

- **Normalizar la puntuación de la pregunta.** Quitar el "?" haría el resultado estable, pero de la peor forma: sin "?", la fusión en dos niveles da 0.81.
- **Darle más peso a la variante.** Agrega un parámetro que habría que ajustar mirando el banco (sobreajuste).
- **Subir `ef_search` de HNSW.** Reduce los vecinos omitidos, pero no los elimina. Con unos 250 chunks por juego, la búsqueda exacta cuesta milisegundos. Con un corpus grande habría que volver a HNSW con un `ef_search` alto.

## Consecuencias

- **El sistema no depende del signo de pregunta** (lo verifica un test sobre el banco) y la búsqueda semántica es determinista (lo verifica un test contra la fuerza bruta).
- **Siguen fallando 3 de 36:** `direct_04` y `exact_01` (Level ↔ Dungeon) y `team_08` "where do i get bombs?" (rank 11).
- **Cautela:** el cambio se evaluó sobre el mismo banco. No tiene parámetros y se confirmó fuera del banco, pero 1 caso equivale a 0.03 en el total y a 0.125 en el conjunto del equipo.
