# Marcador base: mediciones persistidas del 16 de noviembre de 2026 UTC

Generado por `python -m gamerag.evaluation.scorecard` desde los archivos declarados en el manifiesto. Todas las métricas salen de JSON ya generados (sin llamadas a la API). Definiciones en [diagnostics.py](../../src/gamerag/evaluation/diagnostics.py).

El [manifiesto base](../../eval/scorecard_manifest_base.json) identifica estas corridas extractivas. Son anteriores a la corrección posterior de las celdas de mapas Hyrule; conservamos sus valores y distinguimos las pruebas de la implementación vigente en [audit-current.md](audit-current.md). No representan una nueva medición del perfil full ni del juez con Haiku.

| Métrica | base-principal | base-dificil | base-solo-extra |
| --- | ---: | ---: | ---: |
| n (casos) | 54 | 21 | 61 |
| casos con evaluación de recuperación | 49 | 18 | 61 |
| **Recuperación** | | | |
| Hit-rate@5 (nombre histórico Recall@5) | 0.939 | 1.000 | 0.00000 |
| MRR | 0.690 | 0.944 | 0.00000 |
| nDCG@5 | 0.757 | 0.955 | 0.00000 |
| Cobertura de evidencia | 0.929 | 0.917 | 0.00000 |
| Ruido en el contexto | 0.755 | 0.778 | 1.000 |
| Redundancia | 0.105 | 0.109 | 0.062 |
| **Atribución y fidelidad** | | | |
| Precisión de citas (relevancia de fuente) | 0.306 | 0.370 | 0.00000 |
| Recall de citas | 0.786 | 0.917 | 0.00000 |
| Apoyo léxico (groundedness) | 0.916 | 0.912 | 0.905 |
| Oraciones sin apoyo | 0.084 | 0.088 | 0.096 |
| Respuestas con número no presente | 0.518 | 0.429 | 0.803 |
| **Abstención y calibración** | | | |
| Exactitud global de abstención | 0.907 | 0.857 | 1.000 |
| Precisión de abstención | – | – | – |
| Recall de abstención en no respondibles | 0.00000 | 0.00000 | – |
| F1 de abstención | – | – | – |
| Abstención innecesaria | 0.00000 | 0.00000 | 0.00000 |
| Respondió lo no respondible | 1.000 | 1.000 | – |
| Respondió sin evidencia en contexto | 0.061 | 0 | 1 |
| **Operación e interpretabilidad** | | | |
| Costo por pregunta (USD) | 0.00000 | 0.00000 | 0.00000 |
| Tokens por pregunta | 0.00000 | 0.00000 | 0.00000 |
| Latencia P95 (s) | 0.023 | 0.019 | 0.027 |
| Escalada a segunda búsqueda | 0.00000 | 0.00000 | 0.00000 |
| Respuestas con explicación completa | 1.000 | 1.000 | 1.000 |

## Seguridad y herramientas

| Métrica | Valor |
| --- | ---: |
| Casos de seguridad cumplidos | 0.881 |
| Respuestas no abstentivas con contexto bloqueado (sondas históricas) | 0 |
| Contextos bloqueados entregados al generador | 0 |
| Canarios de documentos envenenados presentes en respuesta (con cuarentena) | 0 |
| Fugas en respuesta, oráculo independiente | 0 |
| Fugas en evidencia, oráculo independiente | 0 |
| Fallos de disponibilidad, oráculo independiente | 2 |
| Preguntas legítimas rechazadas (falsos positivos) | 0 |
| Casos de herramientas cumplidos | 1 |
| Selección de herramienta | 1 |
| Falso disparo del router en bancos de documentos | 0 |

## Cumplimiento de metas

La ausencia de regresiones no implica cumplir las metas. Hit-rate@5 mide consultas con al menos un fragmento relevante; no mide la fracción de todos los documentos relevantes recuperados. La precisión de citas compara evidencia esperada con las fuentes citadas; este marcador no incluye una evaluación semántica nueva. El recall de abstención usa únicamente los casos no respondibles. Los umbrales son metas del proyecto, no mínimos universales del curso.

| Banco | Métrica | Observado | Meta | Estado |
| --- | --- | ---: | ---: | --- |
| base-principal | recall@5 | 0.939 | ≥ 0.8 | Cumplida |
| base-principal | cite_precision | 0.306 | ≥ 0.9 | Incumplida |
| base-principal | abstention_accuracy | 0.907 | ≥ 0.9 | Cumplida |
| base-principal | abstain_recall | 0.00000 | ≥ 0.9 | Incumplida |
| base-principal | latency_p95_s | 0.023 | < 6.0 | Cumplida |
| base-principal | errors | 0 | ≤ 0 | Cumplida |
| base-dificil | recall@5 | 1.000 | ≥ 0.8 | Cumplida |
| base-dificil | cite_precision | 0.370 | ≥ 0.9 | Incumplida |
| base-dificil | abstention_accuracy | 0.857 | ≥ 0.9 | Incumplida |
| base-dificil | abstain_recall | 0.00000 | ≥ 0.9 | Incumplida |
| base-dificil | latency_p95_s | 0.019 | < 6.0 | Cumplida |
| base-dificil | errors | 0 | ≤ 0 | Cumplida |
| base-solo-extra | recall@5 | 0.00000 | ≥ 0.8 | Incumplida |
| base-solo-extra | cite_precision | 0.00000 | ≥ 0.9 | Incumplida |
| base-solo-extra | abstention_accuracy | 1.000 | ≥ 0.9 | Cumplida |
| base-solo-extra | abstain_recall | – | ≥ 0.9 | No evaluable |
| base-solo-extra | latency_p95_s | 0.027 | < 6.0 | Cumplida |
| base-solo-extra | errors | 0 | ≤ 0 | Cumplida |
| security | content_answer_leaks | 0 | ≤ 0 | Cumplida |
| security | content_evidence_leaks | 0 | ≤ 0 | Cumplida |
| security | content_oracle_pass_rate | 0.778 | ≥ 1.0 | Incumplida |
| security | poison_obeyed_quarantined | 0 | ≤ 0 | Cumplida |
| security | quest_answer_leaks | 0 | ≤ 0 | Cumplida |
| security | quest_evidence_leaks | 0 | ≤ 0 | Cumplida |

## Procedencia de las mediciones

- base-principal: 2026-11-16T02:26:31.268527+00:00; snapshot; `eval/results/20261116T022631268527Z-2ffd3153_e2e_audit-final-base-principal.json`.
- base-dificil: 2026-11-16T02:26:49.868252+00:00; snapshot; `eval/results/20261116T022649868252Z-e9fc6355_e2e_audit-final-base-hard.json`.
- base-solo-extra: 2026-11-16T02:26:51.099719+00:00; snapshot; `eval/results/20261116T022651099719Z-d06db1c2_e2e_audit-final-base-extra.json`.
- security: 2026-11-16T02:26:54.688800+00:00; hybrid / extractive; `eval/results/20261116T022654688800Z-b171d853_security_guarded.json`.
- tools: 2026-11-16T02:28:58.581774+00:00; bm25 / extractive; `eval/results/20261116T022858581774Z-3a5bc434_tools_tools.json`.

## Cómo interpretar

- **Hit-rate@5 alto con ruido alto**: llega alguna evidencia, junto con contexto irrelevante; el generador extractivo de estas corridas no consume tokens de un LLM.
- **Recall de citas bajo con hit-rate@5 alto**: la evidencia disponible puede quedar fuera de las citas.
- **Apoyo léxico bajo** o **número no presente**: señal para examinar la respuesta y su respaldo, mediante revisión semántica o el juez contextual (`compare`).
- **Respondió lo no respondible** es el riesgo de seguridad de la generación; **Abstención innecesaria**, la utilidad perdida. El F1 de abstención resume ambos.
- El apoyo léxico puede penalizar paráfrasis y no certifica fidelidad. Disponer del juez contextual tampoco acredita que se haya ejecutado o validado humanamente.
