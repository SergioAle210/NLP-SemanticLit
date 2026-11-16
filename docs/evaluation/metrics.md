# Métricas, artefactos y comparación

La evaluación cubre recuperación, respuesta, operación y seguridad (§9 del curso). La API y `evaluation.e2e` reutilizan el pipeline, pero E2E invoca `Pipeline.ask` directamente: sus tiempos excluyen transporte HTTP, Gradio, arranque, bootstrap y carga inicial de modelos. `evaluation.retrieval` compara los recuperadores directamente, sin perfil ni controles de acceso; sus resultados no acreditan la seguridad del contexto servido.

## Ejecución reproducible

Después de preparar el entorno y el corpus:

```powershell
uv run --no-sync python -m gamerag.evaluation.retrieval zelda1 --retriever bm25 --chunker structural
uv run --no-sync python -m gamerag.evaluation.e2e --serving-profile base --retriever hybrid --cases eval/cases.jsonl --label base-principal
uv run --no-sync python -m gamerag.evaluation.tools_eval
uv run --no-sync python -m gamerag.evaluation.versions --dense
uv run --no-sync python -m gamerag.evaluation.security --serving-profile base --retriever hybrid --offline
```

`--serving-profile` selecciona `base` o `full`; `--profile` de E2E selecciona el perfil del jugador. Una configuración `full` debe verificarse en los metadatos efectivos: una clave ausente no demuestra generación remota. El modo `base` utiliza un generador extractivo y no reemplaza una nueva medición de calidad con Haiku.

## Recuperación: definición y denominador

| Medida | Cálculo | Interpretación |
| --- | --- | --- |
| Hit rate@k | Fracción de consultas con al menos un chunk relevante entre las primeras k posiciones | Los campos históricos `recall@k` y `ctx_recall` representan esta medida |
| Precision@k | Chunks relevantes en las primeras k posiciones / k | El denominador es k, incluso si la lista tiene menos elementos |
| MRR | Media de 1/rango del primer relevante; cero si no aparece | Describe posición del primer acierto |
| Cobertura de evidencia | Partes de evidencia esperadas presentes en la unión del contexto / partes esperadas | Distingue recuperación parcial en consultas compuestas |
| Ruido | Chunks sin partes de evidencia / chunks del contexto | Solo se calcula donde hay contexto evaluable |
| Redundancia | Jaccard medio de términos de contenido entre pares de chunks | Aproximación léxica a repetición |
| nDCG@5 de diagnóstico | Ganancia binaria descontada y normalizada con los relevantes observados | Normalización local al contexto; no utiliza todos los documentos relevantes del corpus |

El recall documental fraccional es la proporción de documentos relevantes recuperados sobre todos los relevantes de la colección. No lo equiparamos con el hit rate implementado. La cobertura usa partes de evidencia, otra unidad diferente. Los nombres históricos permanecen para compatibilidad, acompañados de alias y definiciones correctas.

Para expresar Recall@k con la anotación disponible, utilizamos **unidades de evidencia**: cada parte esperada del caso cuenta una vez, aunque aparezca en varios chunks. Su recall es `partes esperadas recuperadas entre los primeros k chunks / total de partes esperadas`. El evaluador de recuperación ya calcula esa cantidad como `coverage@k`, mediante `coverage_at_k`, para k = 1, 3, 5 y 10. Al presentarla como recall de evidencia debemos conservar esa unidad y denominador; no representa recall de todos los documentos relevantes del corpus. En E2E, `ctx_coverage` usa todo el contexto final, cuyo tamaño puede variar por búsqueda secundaria: no debe rotularse automáticamente como Recall@5. No cambiamos valores ni nombres de los resultados históricos.

Las preguntas no respondibles se excluyen de recuperación. El evaluador E2E calcula recuperación en casos respondibles de sus categorías documentales; el diagnóstico filtra además la ruta documental y la existencia de evidencia esperada. Cada reporte conserva la cantidad evaluable y no convierte un denominador ausente en cero rendimiento.

La relevancia se determina por partes textuales y sus alternativas en el banco, según [ADR-0008](../architecture/decisions/0008-relevance-by-evidence-text.md). No depende de un `chunk_id` fijado a una segmentación: un cambio de chunking puede conservar la misma evidencia en otra posición.

## Respuesta y citas

| Medida | Qué verifica | Qué no demuestra |
| --- | --- | --- |
| Integridad de cita | Triple `source/page/chunk_id` dentro de evidencia autorizada | Que cada afirmación esté respaldada |
| `cite_precision` | Fracción de chunks citados que contienen evidencia esperada; promedio por caso evaluable sin abstención | Precisión factual por afirmación |
| `cite_recall` | Partes esperadas cubiertas por las citas / partes esperadas | Ausencia de afirmaciones adicionales |
| `groundedness` | Coincidencia de palabras de contenido entre oración y respaldo | Entailment semántico; puede penalizar paráfrasis |
| `unsupported_rate` | Oraciones con apoyo léxico inferior a 0.5 | Una tasa de alucinación validada por humanos |
| `novel_number_rate` | Respuestas con un número ausente del contexto | Que todo número nuevo sea necesariamente incorrecto |

La evidencia de esquema 2 es el texto exacto autorizado, incluidas proyecciones. El evaluador verifica su hash, los IDs y las citas completas antes de calcular métricas. Los artefactos históricos sin evidencia embebida requieren resolver todos sus identificadores; no se omiten silenciosamente los faltantes.

## Juez y revisión humana

El juez de `evaluation.compare` recibe pregunta, comportamiento esperado, respuesta, citas y evidencia final autorizada. Conserva el prompt versionado, entradas, razonamiento breve, resultado, costo y errores. No utiliza conocimiento externo como respaldo de una afirmación.

| Campo del juez | Valores o cálculo |
| --- | --- |
| `correct` | Correcta = 1; parcial = 0.5; incorrecta = 0 |
| `faithfulness_score` | Respaldada = 1; parcial = 0.5; sin respaldo = 0 |
| `factual_coverage` | Partes esperadas respondidas y respaldadas / partes esperadas |
| `citation_support_precision` | IDs citados que apoyan una afirmación / IDs citados |
| `judge_error` | Error o presupuesto agotado; las métricas no obtenidas quedan nulas |

Los casos con abstención, error o etiqueta no respondible se resuelven mediante la regla determinista de abstención y se identifican como tales. No se rellenan fidelidad o cobertura semántica inexistentes.

```powershell
uv run --no-sync python -m gamerag.evaluation.compare A.json B.json --cases eval/cases.jsonl --label comparacion-pareada
```

`A.json` y `B.json` deben sustituirse por rutas de artefactos con los mismos IDs y el banco compatible. El juez puede efectuar llamadas al proveedor dentro del presupuesto configurado. Su implementación y sus pruebas no acreditan una evaluación real nueva ni revisión humana. No existe una validación humana completa del juez registrada en esta revisión.

El curso exige evaluación cuantitativa y cualitativa de fidelidad, cobertura, relevancia, citas y abstención; no prescribe un juez LLM ni una revisión humana completa de ese juez. La validación humana es un método recomendable para contrastar nuestros indicadores, no un requisito adicional que debamos atribuir a las instrucciones oficiales. Los indicadores léxicos disponibles y la ausencia de una nueva ejecución semántica del juez delimitan la evidencia actual.

## Abstención

Consideramos positiva la clase «debe abstenerse». TP corresponde a abstención en casos no respondibles; FP, a abstención innecesaria; FN, a responder un caso no respondible; TN, a responder uno respondible.

| Medida | Fórmula |
| --- | --- |
| Corrección global | (TP + TN) / casos sin error |
| Precisión de abstención | TP / (TP + FP), con denominador y disponibilidad declarados |
| Sensibilidad de abstención | TP / (TP + FN) |
| F1 | Media armónica de precisión y sensibilidad cuando están definidas |
| Abstención innecesaria | FP / casos respondibles |
| Respuesta no debida | FN / casos no respondibles |

El reporte incluye la matriz y los errores excluidos. Un banco sin preguntas no respondibles no permite estimar sensibilidad de abstención. Una corrección global de 1.00 en un generador que responde siempre tampoco demuestra que sus respuestas sean correctas.

## Operación

La latencia se mide alrededor de `ask`, con `perf_counter`, y se guarda por consulta. El P95 utiliza la posición `floor(0.95 × (n − 1))` de la lista ordenada; el método queda declarado en metadatos. Comparaciones entre equipos, caché o perfiles distintos necesitan esa salvedad.

La telemetría se captura por solicitud, sin restar contadores globales concurrentes. `llm_call_count` cuenta eventos de modelo, incluidos intentos, caché y bloqueos. `http_call_count` identifica intentos HTTP reales; `http_retry_count` cuenta intentos posteriores al primero. Se conservan errores, llamadas con uso desconocido y solicitudes degradadas.

Los tokens y el costo provienen del uso observado o registrado y de precios configurados. El control de presupuesto serializa comprobación, llamada y registro dentro de un proceso; no garantiza coordinación multiproceso ni reproduce una factura del proveedor.

## Seguridad, versiones y comparación

El [reporte de seguridad](../security/report.md) separa suite adversaria, acceso, envenenamiento y oráculos independientes. Los oráculos inspeccionan respuesta y evidencia con patrones predeclarados, sin deducir lo prohibido del mismo filtro que evalúan. Una respuesta sin fuga puede fallar porque omite información permitida.

`evaluation.versions --dense` reingesta dos revisiones de un documento sintético en la misma ruta, reconstruye el índice y verifica respuesta, cita, revisión y cambio de huella. Se ejecuta con E5 local y no añade un filtro temporal a la API. Sus dos casos se distinguen de las variantes de quest y nombres regionales.

Las comparaciones deben conservar banco, configuración, modo de caché y semántica de métricas. Los ADRs y [resultados históricos](results.md) mantienen experimentos de chunking, embeddings, expansión y reranking. No se afirma haber ejecutado ablaciones de un G4 completo o de memoria conversacional.

## Artefactos y metas

Cada corrida de esquema 2 guarda un identificador único, fecha UTC, hash del banco, corpus, configuración e implementación, commit y estado de trabajo, configuración pública y `human_review: false`. E2E registra huellas de implementación al inicio y final para señalar cambios durante una ejecución. Los resultados se crean con nombre único; no sobrescriben corridas previas.

Esta política corresponde a E2E, comparación, herramientas, seguridad, oráculos y revisiones documentales. El evaluador histórico `evaluation.retrieval` conserva nombres por fecha/juego/variante y puede reemplazar una corrida de la misma variante y día; no produce automáticamente el esquema 2. Debemos preservar el resultado anterior antes de repetir ese experimento.

El scorecard distingue regresión frente a una referencia y cumplimiento de metas: hit rate@5 ≥ 0.80, citas ≥ 0.90 y P95 < 6 s, según la política declarada. La corrección y sensibilidad de abstención aparecen separadas. `--check` y `--check-targets` son verificaciones de lectura; actualizar una referencia exige una acción explícita. Los valores son metas del proyecto, no umbrales universales del curso.
