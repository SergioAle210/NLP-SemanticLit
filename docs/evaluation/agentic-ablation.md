# Ablación agéntica (extremo a extremo) — primera medición

Fecha: 2026-11-08 · Modelo: `claude-haiku-5-5` · Recuperador: **BM25 + expansión de consulta** (el extra
`semantic` no estaba instalado; el híbrido de producción llega a Recall@5 ≈ 0.94–1.00, así que aquí hay más
margen de mejora que en producción) · Banco: 54 casos (49 con respuesta, 5 sin) · Una sola corrida por
configuración, sin caché (costo real). Reproducir: `uv run python -m gamerag.evaluation.e2e [--generator haiku] [--evidence]`.
Resultados por caso: `eval/results/2026-11-08_e2e_*.json`.

| Configuración | ctx_recall | abstención correcta | precisión de citas | costo/pregunta | latencia media / P95 |
|---|---|---|---|---|---|
| L0 extractivo (sin LLM) | 0.796 | 0.926 | 0.265 | $0 | 2 ms / 4 ms |
| L1 grafo + Haiku | 0.796 | 0.852 | 0.746 | $0.00024 | 1.6 s / 2.2 s |
| L2 grafo + Haiku + evaluador de evidencia y reescritura | **0.857** | **0.926** | 0.724 | $0.00051 | 4.0 s / 4.8 s |

Gasto total de las tres corridas: $0.041 (tope del proyecto: $15).

## Lectura

- **Haiku sube mucho la precisión de citas** (0.27 → 0.75): el extractivo cita 3 fragmentos siempre; Haiku
  cita solo lo que usó. No mejora el contexto (mismo recuperador).
- **El evaluador recupera 4 casos y pierde 1** (neto +3 de 49, +6 pt de ctx_recall) y arregla los casos sin
  respuesta (abstención 0.75 → 1.00 en `unanswerable`). Cuesta ×2.1 por pregunta y ×2.5 de latencia.
- **Riesgo observado:** las reescrituras a veces inventan contexto ("Zelda II", "Link's Awakening") y una
  rompió un caso que ya acertaba (`zelda_version_01`). Hay que restringir el prompt de reescritura al juego
  activo y a términos del glosario.
- **Casos que siguen sin evidencia** (7): `zelda_direct_01`, `zelda_exact_01/02`, `zelda_version_01`,
  `zelda_team_04`, `zelda_extra_02`, `ng_robust_02`. Los exactos (`Level-4`, `D-4`) son de recuperación
  léxica/estructural, no de reescritura.

## Límites de esta medición

n = 49 con una corrida cada una (Haiku no es determinista): las diferencias de 1–3 casos no son
concluyentes. Falta repetir con el recuperador híbrido, medir fidelidad con un juez, y los casos de
seguridad/spoilers (solo está el gate G1).

---

## Repetición con el recuperador híbrido (BM25 + e5-small-multi + RRF)

Mismas condiciones (una corrida por configuración, sin caché). Gasto acumulado del proyecto tras ambas
mediciones: $0.083.

| Configuración | ctx_recall | abstención correcta | precisión de citas | costo/pregunta | latencia media / P95 |
|---|---|---|---|---|---|
| L0 extractivo | 0.959 | 0.907 | 0.313 | $0 | 0.07 s / 0.11 s |
| L1 grafo + Haiku | 0.959 | 0.926 | 0.767 | $0.00026 | 2.2 s / 2.0 s |
| L2 + evaluador y reescritura | 0.959 | 0.944 | 0.718 | $0.00052 | 3.2 s / 4.7 s |

**Conclusión: con el híbrido el evaluador de evidencia no mejora la recuperación en este banco.** El contexto
ya acierta en 47 de 49 casos; la reescritura cambia dos casos de signo (`ng_robust_03` gana, `ng_robust_02`
pierde) y se activa en el 30 % de las preguntas. La abstención sube un caso (0.926 → 0.944, dentro del
ruido) y la precisión de citas baja 5 pt. A cambio duplica el costo por pregunta y suma ~1 s de latencia.
La ganancia de +6 pt vista con BM25 era, sobre todo, compensar un recuperador más débil.

Quedan sin evidencia `zelda_exact_01` (el viejo del Level-4: consulta de ID exacto) y `ng_robust_02`.
`zelda_version_01` y `ng_unanswerable_01` fallan en abstención con Haiku.

**Implicaciones:**
- El evaluador debe dejar de ser el nodo por defecto; conviene activarlo solo cuando la recuperación es débil
  (p. ej. puntaje máximo bajo o contexto vacío), no en cada consulta.
- El techo restante no está en la reescritura sino en consultas con identificadores exactos y en la calibración
  de la abstención del generador: ahí van la siguiente mejora y las pruebas con más casos.
- Con solo 49 casos y una corrida, ninguna diferencia de 1–2 casos es concluyente.

---

## Evaluador condicional (`evidence_mode=on_abstain`)

Un umbral sobre el puntaje de recuperación **no** separa aciertos de fallos (el puntaje del primer resultado
de los casos fallidos cae en el mismo rango que el de los acertados, tanto en BM25 como en el híbrido), así que
la compuerta usa otra señal: el evaluador y la reescritura solo intervienen **si el generador se abstiene**
(evalúa, reescribe y regenera, máx. 1 reintento). Las preguntas que ya se responden no pagan nada extra.

| Recuperador | Configuración | ctx_recall | abstención | precisión de citas | costo/pregunta | latencia media / P95 |
|---|---|---|---|---|---|---|
| híbrido | grafo + Haiku | 0.959 | 0.926 | 0.767 | $0.00026 | 2.2 s / 2.0 s |
| híbrido | evaluador siempre | 0.959 | 0.944 | 0.718 | $0.00052 | 3.2 s / 4.7 s |
| híbrido | **evaluador si se abstiene** | 0.959 | 0.926 | 0.756 | $0.00031 | 1.7 s / 3.3 s |
| BM25 | grafo + Haiku | 0.796 | 0.852 | 0.746 | $0.00024 | 1.6 s / 2.2 s |
| BM25 | evaluador siempre | 0.857 | 0.926 | 0.724 | $0.00051 | 4.0 s / 4.8 s |
| BM25 | **evaluador si se abstiene** | 0.837 | 0.907 | 0.709 | $0.00031 | 1.7 s / 3.6 s |

Se interviene en el 9 % (híbrido) y el 15 % (BM25) de las preguntas.

**Lectura:** con el recuperador débil (BM25), el modo condicional conserva ~2/3 de la mejora de contexto
(+4 pt frente a +6 pt) a ~40 % del costo extra. Con el híbrido de producción no mejora ninguna métrica frente
al grafo simple (+20 % de costo, sin ganancia): el banco ya está saturado en recuperación. El modo condicional
queda como red de seguridad barata (por defecto), no como mejora medible sobre este banco; para demostrar valor
hace falta un banco más difícil (consultas ambiguas, multi-salto, identificadores exactos).

---

## Segunda búsqueda en las wikis extra (2026-11-08)

Sumar las wikis extra al índice principal **empeora** la recuperación de Zelda 1 y Ninja Gaiden (contexto con
evidencia 0.959 → 0.755; Recall@5 de Zelda 1 0.97 → 0.69; un reranker no lo repara: 0.61). Zeldapedia y zeldawiki
cubren toda la serie y ocupan los primeros puestos. Por eso las wikis extra se consultan como **segundo nivel**: solo
si el generador se abstiene y el evaluador de evidencia dice "insuficiente" se busca (una vez) en un índice aparte de
las wikis extra y se agregan hasta 3 chunks al contexto (`GAMERAG_SECONDARY_SEARCH=true`).

Banco principal (54 casos, híbrido + Haiku, evaluador si se abstiene), sin y con segunda búsqueda:

| Métrica | Sin secundaria | Con secundaria |
|---|---|---|
| Contexto con evidencia | 0.959 | 0.980 |
| Corrección (juez LLM) | 0.815 | 0.843 |
| Abstención correcta | 0.926 | 0.926 |
| Precisión de citas | 0.773 | 0.788 |
| Costo / pregunta | $0.00031 | $0.00036 (+17 %) |
| Latencia media | 1.84 s | 2.11 s |
| Preguntas que usan la secundaria | – | 9 % (5 de 54) |

Lectura: no hay daño (a diferencia de mezclar todo: −20 pts) y el costo extra solo lo pagan las preguntas
difíciles (~2× en esas 5). La mejora de corrección (+2.8 pts: 5 casos mejoran, 2 empeoran) está dentro del ruido
(±2 casos) y, en los 5 casos donde se usó, no cambia (0.80 → 0.80): el banco ya está cubierto por StrategyWiki, así
que no puede mostrar el valor de la secundaria. Para medirlo hacen falta preguntas que solo respondan las wikis
extra (juegos nuevos con su banco, o preguntas generadas desde chunks de esas wikis).

## Segunda búsqueda sobre un banco que solo responden las wikis extra (`eval/cases_extra.jsonl`, 84 casos)

Banco generado con `gamerag.evaluation.extra_bank`: 12 preguntas por juego a partir de pasajes de las wikis extra, con cita
literal verificada y un filtro léxico que descarta las que StrategyWiki ya responde. Retriever híbrido + Haiku. Correctitud
por juez LLM (`compare`).

| Configuración | correct | ctx_coverage | cite_precision | $/pregunta | latencia |
|---|---|---|---|---|---|
| A: solo StrategyWiki (+ evaluador si se abstiene) | 0.03 | 0.00 | 0.00 | 0.0006 | 3.2 s |
| B: A + segunda búsqueda en wikis extra | 0.64 | 0.64 | 0.66 | 0.0008 | 3.7 s |
| C: todo mezclado en un índice | 0.89 | 0.94 | 0.79 | 0.0003 | 1.8 s |

- B mejora a A en 54 casos y no empeora en ninguno (A casi nunca acierta: el banco es, por construcción, contenido ajeno a la fuente principal). La segunda búsqueda se activó en 75 % de las preguntas.
- C supera a B aquí (0.89 vs 0.64; B gana en 1 caso, C en 27) y es más barato: este banco favorece al índice mezclado porque todas las preguntas salen de las wikis extra.
- Esto **no invalida** B: C degrada el banco principal (Zelda 1 contexto con evidencia 0.959→0.755; Recall@5 0.97→0.69). B mantiene intacto el banco principal y recupera ~72 % de lo que logra C en contenido solo-extra. Es un compromiso, no una victoria.
- Falta: medir si un enrutamiento por pregunta (mezclar solo cuando el evaluador lo pide, sin la ruta de reescritura) cierra la brecha B–C.

Salvedades: (1) la corrida B tuvo una condición de carrera de Chroma en Zelda 1 en la ejecución completa; esos 12 casos se tomaron de una corrida aparte con la misma configuración y se anotó en el JSON (`run.note`). (2) El banco lo escribió el mismo modelo familia Haiku que responde y el juez es un LLM; las cifras absolutas son indicativas. (3) El filtro léxico es aproximado.

### Seguimiento: ¿cerrar la brecha B–C mezclando solo al escalar? (mismo banco, 84 casos, sin errores)

Se agregó `secondary_mode`: `append` (B: suma 3 chunks de las wikis extra) o `mixed` (D: ante evidencia insuficiente, el
contexto se reemplaza con los 5 mejores de un índice con todas las wikis; los gates siguen aplicando). Se corrigió además un
fallo del evaluador de evidencia: con `max_tokens=200` devolvía JSON truncado y, al ser fail-open, **la pregunta nunca
escalaba** (22 de 84 casos). Con 500 tokens la escalada pasó de 75 % a 83 %.

| Config | correct | ctx_coverage | cite_precision | $/preg |
|---|---|---|---|---|
| A: solo StrategyWiki | 0.03 | 0.00 | 0.00 | 0.0006 |
| B: añade 3 chunks extra | 0.68 | 0.71 | 0.71 | 0.0010 |
| D: reemplaza por índice mezclado | 0.74 | 0.73 | 0.67 | 0.0010 |
| C: todo mezclado siempre | 0.89 | 0.94 | 0.79 | 0.0003 |

- D mejora a B (+6 puntos; gana en 9 casos y pierde en 4) con menos precisión de citas; es una diferencia pequeña con n=84.
- La brecha con C (0.74 vs 0.89) **no se cierra**. Ahora el límite es el 17 % de casos que no escalan: el generador responde con
  confianza desde contexto de StrategyWiki irrelevante y en modo `on_abstain` el evaluador no interviene. Probar `--mode always`
  (una llamada extra por pregunta) es el siguiente experimento, pero cuesta más que C.
- Los resultados por juego se corrieron en procesos separados (`--only-game`): Chroma devolvía "Nothing found on disk" al abrir
  los 14 índices en un mismo proceso (afectaba a un juego distinto en cada corrida). La causa raíz no está resuelta; el
  rodeo es `--only-game` / `only_games`.

## Configuración final de la segunda búsqueda (perfil `full`)

Correcciones previas a esta medición, que invalidaban corridas anteriores:

1. **Contaminación entre títulos.** Las páginas de Zeldapedia y ZeldaWiki ("Bow", "Link", ...) describen toda la saga; la
   segunda búsqueda respondía "¿Puedo montar un caballo?" con Epona (que no existe en Zelda 1) y rompía abstenciones
   correctas. Esas fuentes ahora son `scope: franchise` y quedan fuera de la segunda búsqueda
   (`secondary_franchise: false`). El banco extra pasó de 84 a 61 casos (los 23 casos solo-saga quedaron en
   `eval/cases_extra_franchise.jsonl`).
2. **Tope por corrida.** El tope `serve` ($1) se acumulaba para siempre entre procesos y desactivaba Haiku en silencio
   (caía al extractivo). Ahora cuenta solo desde el inicio de cada proceso; el tope total sigue siendo acumulado.
3. **Chroma.** Con ~14 colecciones abiertas, Chroma descartaba el segmento HNSW de una colección pequeña y no podía
   recargarlo. La búsqueda es exacta, así que se leen los vectores con `get` (sin HNSW) y se cargan al abrir el índice.
   Recall@5 sin cambios (Zelda 1 0.97, Ninja Gaiden 0.92).

Resultados (Haiku, híbrido, evaluador `on_abstain`, segunda búsqueda `mixed`, sin errores):

| Banco | n | Config | correct (juez) | ctx_coverage | abstención ok | cite_precision |
|---|---:|---|---:|---:|---:|---:|
| Solo-extra | 61 | A: solo StrategyWiki | 0.04 | 0.00 | 0.11 | 0.00 |
| Solo-extra | 61 | D: + segunda búsqueda | **0.84** | 0.82 | 0.93 | 0.78 |
| Principal | 54 | A | 0.87 | – | 0.944 | 0.753 |
| Principal | 54 | D | 0.84 | – | 0.944 | 0.759 |
| Difícil | 21 | A | 0.81 | – | 0.952 | 0.854 |
| Difícil | 21 | D | 0.88 | – | **1.000** | 0.817 |

- En el banco solo-extra, D recupera de 0.04 a 0.84 de correctitud (50 casos mejoran, 0 empeoran).
- En el principal, D no cambia la recuperación ni las abstenciones. Los 6 casos "peores" del juez **no escalaron** a la
  segunda búsqueda: es varianza de generación/juez entre corridas sin caché. Solo escalaron las 4 preguntas sin respuesta
  (todas se abstuvieron correctamente).
- Con `scope: franchise` ya no hay pérdida de abstenciones en el banco difícil (antes 0.95 → 0.86).
- Decisión: el perfil `full` (`GAMERAG_PROFILE=full`) fija esta configuración. Ver ADR-0014.
