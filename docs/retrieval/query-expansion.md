# Transformación de consultas: ortografía, glosario y multi-consulta

Implementación: [src/gamerag/retrieval/query_expansion.py](../../src/gamerag/retrieval/query_expansion.py). Decisión: [ADR-0010](../architecture/decisions/0010-query-expansion.md).

## Problema: desajuste de vocabulario

Los jugadores no preguntan con las palabras de la wiki:

| El jugador dice | La wiki dice |
| --- | --- |
| attack, hit, fight | swing the sword (Controls: `NES: A`) |
| money, cash, coins | rupees |
| heal, health | refills hearts, life meter |
| menu, inventory | sub-screen |
| secondary item | subweapon (`NES: B`) |
| atack, bombz (errores de tipeo) | attack, bombs |

Ni el reranker ni el chunking por fila resolvieron esto ([evaluation/results.md](../evaluation/results.md)), porque no es un problema de orden ni de dilución: la respuesta usa **otras palabras**, y otros chunks sí contienen la palabra del jugador (enemigos que "attack").

## Estrategia (curso, tema 08, diapositivas 211-212)

```text
pregunta original ──────────────────────────────┐
     │                                          ├─► búsqueda híbrida (cada una) ─► fusión RRF ─► top-k
     └─► corrección ortográfica ─► glosario ────┘
         "how do i atack?" → "how do i attack? swing the sword A button"
```

1. **Corrección ortográfica conservadora.** Una palabra se corrige solo si:
   - tiene **5 o más letras** (las cortas tienen demasiados vecinos válidos: "cost" → "coast");
   - **no aparece ni una vez** en el corpus ni en el glosario ("across" no se toca; "heal" se expande, no se corrige);
   - existe una palabra del vocabulario (frecuencia ≥ 2) **con la misma primera letra** a **distancia de edición 1** ("atack" → "attack", "bombz" → "bombs"). La distancia es Damerau-Levenshtein restringida: además de insertar, borrar o cambiar una letra, **intercambiar dos letras vecinas** cuenta como una sola operación ("shiled" → "shield"). Con Levenshtein, ese intercambio valdría 2.
2. **Glosario por juego** (`query_expansion.synonyms` en `config/games/<juego>.yaml`): si la pregunta contiene un término del jugador, se **agregan** los términos del juego. Nada se borra.
3. **Multi-consulta:** se busca con la **pregunta original** y con la **variante**, cada una con la profundidad fija de 20, y las listas se fusionan con RRF. **La original se conserva siempre**, tanto para la auditoría (`trace.query_variants`) como para que una variante mala no cambie la intención.
   - **La fusión es plana** ([ADR-0011](../architecture/decisions/0011-flat-fusion-exact-dense.md)): un solo RRF sobre las 4 listas (BM25 y e5 × original y variante). La fusión en dos niveles (primero por variante y después entre variantes) perdía el acuerdo entre recuperadores y dependía del "?" final.

## Glosario de Zelda

Criterio: equivalencias **generales** de terminología del juego (páginas Controls e Items), no frases de casos de prueba. Se puede ver en [config/games/zelda1.yaml](../../config/games/zelda1.yaml).

**Reglas de identificadores descartadas:** "Level-3" → "dungeon 3" y "first quest" → "quest 1" bajaron el Recall@5 del curso de 0.89 a 0.78 en la ablación sin mejorar nada más. Agregar "dungeon N quest 1" favorece a todos los recorridos de mazmorras, porque todos tienen "Quest" y "Dungeon" en el título. El mecanismo (`rewrites`) queda disponible, pero vacío.

## Glosario de Ninja Gaiden

Se aplica el mismo criterio que en Zelda: la terminología sale de las páginas Gameplay (Controls, Player, Status bar) e Items de [config/games/ninja_gaiden_nes.yaml](../../config/games/ninja_gaiden_nes.yaml). Se escribió **después** del mini banco de NG.

- **Acciones:** attack/hit/fight → "B button", "swinging your sword"; jump → "A button"; pause → "Start button".
- **Recursos:** ninpo/magic/mana → "spirit points" ("ninpo" no aparece nunca en la wiki); special/subweapon → "secondary weapon"; shuriken → "throwing star"; sword → "katana"; heal → "restore health", "potion".

**Por qué "attack" necesita glosario aunque la wiki lo use:** aparece en 27 de los 84 chunks de NG (los enemigos atacan), así que su IDF es bajo y no distingue la página de controles.

**Resultado** (13 casos con respuesta):
- Recall@5 pasa de 0.85 a **0.92**; robustez, de 0.50 a 0.75.
- Los 9 casos de tipo curso se mantienen en 1.00.
- "heal" sigue fallando (rank 11), por dilución: el chunk de Items mezcla 5 ítems ([evaluation/results.md](../evaluation/results.md)).

## Resultados

Híbrida e5, chunking estructural ([evaluation/results.md](../evaluation/results.md)):

| | Sin expansión | Con expansión, fusión en dos niveles (ADR-0010) | **Con expansión, fusión plana (ADR-0011, servida)** |
| --- | ---: | ---: | ---: |
| Curso (18) | 0.89 | 0.89 | **0.89** |
| **Equipo (8, preguntas escritas sin ver el corpus)** | 0.50 | 0.75 | **0.88** |
| Robustez (18) | 0.56 | 0.83 | **0.89** |
| Total (36) | 0.72 | 0.86 (0.81 sin "?") | **0.92 (también sin "?")** |
| Latencia media | 20 ms | 29 ms | 44 ms |

## Límites y riesgos

- **Sobreajuste:** el glosario se escribió después de ver qué preguntas fallaban. La mejora en el conjunto del equipo es real, pero **no es una medición independiente** del glosario. La validación correcta es una **segunda tanda de preguntas del equipo**, escrita con el glosario ya congelado.
- **Mantenimiento:** el glosario es manual y por juego. La reescritura con un LLM (Haiku) generalizaría a formulaciones no previstas; queda como comparación cuando esté la API key.
- **Sin diccionario de inglés:** la corrección no sabe si una palabra ausente del corpus es válida en inglés. Por eso es conservadora: prefiere no corregir antes que corregir mal.
- **Correcciones falsas medidas:** se pasaron por el corrector 17,123 palabras inglesas válidas (de 5 o más letras) que no aparecen en el corpus; se tomaron del vocabulario del tokenizador de bge-small. Se "corrigen" 832, el 4.9%:
  - el 39% son flexiones ("plays" → "play", "throws" → "throw"), que no dañan la búsqueda;
  - el resto son errores ("whale" → "while", "older" → "order").

  El daño es acotado porque la pregunta original siempre participa en la búsqueda. La transposición solo agregó 5 a esa cifra (dos de ellas inocuas: "centre" → "center", "metre" → "meter"). La forma de reducirlas es un diccionario de inglés como lista de palabras válidas; queda pendiente.
