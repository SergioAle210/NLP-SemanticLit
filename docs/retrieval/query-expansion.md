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
   - existe una palabra del vocabulario (frecuencia ≥ 2) **con la misma primera letra** a **distancia de edición 1** ("atack" → "attack", "bombz" → "bombs").
2. **Glosario por juego** (`query_expansion.synonyms` en `config/games/<juego>.yaml`): si la pregunta contiene un término del jugador, se **agregan** los términos del juego. Nada se borra.
3. **Multi-consulta:** se busca con la **pregunta original** y con la **variante**, cada una con la profundidad fija de 20, y los rankings se fusionan con RRF. **La original se conserva siempre**, tanto para la auditoría (`trace.query_variants`) como para que una variante mala no cambie la intención.

## Glosario de Zelda

Criterio: equivalencias **generales** de terminología del juego (páginas Controls e Items), no frases de casos de prueba. Se puede ver en [config/games/zelda1.yaml](../../config/games/zelda1.yaml).

**Reglas de identificadores descartadas:** "Level-3" → "dungeon 3" y "first quest" → "quest 1" bajaron el Recall@5 del curso de 0.89 a 0.78 en la ablación sin mejorar nada más. Agregar "dungeon N quest 1" favorece a todos los recorridos de mazmorras, porque todos tienen "Quest" y "Dungeon" en el título. El mecanismo (`rewrites`) queda disponible, pero vacío.

## Resultados

Híbrida e5, chunking estructural ([evaluation/results.md](../evaluation/results.md)):

| | Sin expansión | Con expansión |
| --- | ---: | ---: |
| Curso (18) | 0.89 | 0.89 |
| **Equipo (8, preguntas escritas sin ver el corpus)** | 0.50 | **0.75** |
| Robustez (18) | 0.56 | 0.83 |
| Total (36) | 0.72 | **0.86** |
| Latencia media | 20 ms | 29 ms |

## Límites y riesgos

- **Sobreajuste:** el glosario se escribió después de ver qué preguntas fallaban. La mejora en el conjunto del equipo es real, pero **no es una medición independiente** del glosario. La validación correcta es una **segunda tanda de preguntas del equipo**, escrita con el glosario ya congelado.
- **Mantenimiento:** el glosario es manual y por juego. La reescritura con un LLM (Haiku) generalizaría a formulaciones no previstas; queda como comparación cuando esté la API key.
- **Sin diccionario de inglés:** la corrección no sabe si una palabra ausente del corpus es válida en inglés. Por eso es conservadora: prefiere no corregir antes que corregir mal.
