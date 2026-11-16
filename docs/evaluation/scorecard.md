# Marcador histórico: corridas del 8–9 de noviembre de 2026

Generado por `python -m gamerag.evaluation.scorecard` desde los archivos declarados en el manifiesto. Todas las métricas salen de JSON ya generados (sin llamadas a la API). Definiciones en [diagnostics.py](../../src/gamerag/evaluation/diagnostics.py).

El [manifiesto histórico](../../eval/scorecard_manifest.json) identifica estas mediciones. La ausencia de regresiones compara sus artefactos con la referencia guardada; no prueba el rendimiento del código posterior. La última medición persistida del perfil extractivo está en [scorecard-base.md](scorecard-base.md), y las comprobaciones posteriores se distinguen en [audit-current.md](audit-current.md).

| Métrica | principal | dificil | solo-extra |
| --- | ---: | ---: | ---: |
| n (casos) | 54 | 21 | 61 |
| casos con evaluación de recuperación | 49 | 18 | 61 |
| **Recuperación** | | | |
| Hit-rate@5 (nombre histórico Recall@5) | 0.959 | 1.000 | 0.820 |
| MRR | 0.695 | 0.944 | 0.685 |
| nDCG@5 | 0.765 | 0.955 | 0.720 |
| Cobertura de evidencia | 0.949 | 0.917 | 0.820 |
| Ruido en el contexto | 0.747 | 0.778 | 0.836 |
| Redundancia | 0.100 | 0.107 | 0.080 |
| **Atribución y fidelidad** | | | |
| Precisión de citas (relevancia de fuente) | 0.771 | 0.861 | 0.776 |
| Recall de citas | 0.948 | 0.917 | 0.862 |
| Apoyo léxico (groundedness) | 0.743 | 0.810 | 0.817 |
| Oraciones sin apoyo | 0.147 | 0.102 | 0.050 |
| Respuestas con número no presente | 0.160 | 0.00000 | 0.00000 |
| **Abstención y calibración** | | | |
| Exactitud global de abstención | 0.944 | 1.000 | 0.951 |
| Precisión de abstención | 0.750 | 1.000 | – |
| Recall de abstención en no respondibles | 0.600 | 1.000 | – |
| F1 de abstención | 0.667 | 1.000 | – |
| Abstención innecesaria | 0.020 | 0.00000 | 0.049 |
| Respondió lo no respondible | 0.400 | 0.00000 | – |
| Respondió sin evidencia en contexto | 0.021 | 0 | 0.138 |
| **Operación e interpretabilidad** | | | |
| Costo por pregunta (USD) | 0.00034 | 0.00040 | 0.00075 |
| Tokens por pregunta | 2712.3 | 3163.1 | 6064.1 |
| Latencia P95 (s) | 5.733 | 9.055 | 6.162 |
| Escalada a segunda búsqueda | 0.074 | 0.048 | 0.902 |
| Respuestas con explicación completa | 1.000 | 1.000 | 1.000 |

## Seguridad y herramientas

| Métrica | Valor |
| --- | ---: |
| Casos de seguridad cumplidos | 0.976 |
| Respuestas no abstentivas con contexto bloqueado (sondas históricas) | 0 |
| Contextos bloqueados entregados al generador | 0 |
| Canarios de documentos envenenados presentes en respuesta (con cuarentena) | 0 |
| Fugas en respuesta, oráculo independiente | – |
| Fugas en evidencia, oráculo independiente | – |
| Fallos de disponibilidad, oráculo independiente | – |
| Preguntas legítimas rechazadas (falsos positivos) | 0 |
| Casos de herramientas cumplidos | 1 |
| Selección de herramienta | 1 |
| Falso disparo del router en bancos de documentos | 0 |

## Regresiones frente a la línea base

Ninguna.

## Cumplimiento de metas

La ausencia de regresiones no implica cumplir las metas. Hit-rate@5 mide consultas con al menos un fragmento relevante; no mide la fracción de todos los documentos relevantes recuperados. La precisión de citas compara evidencia esperada con las fuentes citadas; este marcador no incluye una evaluación semántica nueva. El recall de abstención usa únicamente los casos no respondibles. Los umbrales son metas del proyecto, no mínimos universales del curso.

| Banco | Métrica | Observado | Meta | Estado |
| --- | --- | ---: | ---: | --- |
| principal | recall@5 | 0.959 | ≥ 0.8 | Cumplida |
| principal | cite_precision | 0.771 | ≥ 0.9 | Incumplida |
| principal | abstention_accuracy | 0.944 | ≥ 0.9 | Cumplida |
| principal | abstain_recall | 0.600 | ≥ 0.9 | Incumplida |
| principal | latency_p95_s | 5.733 | < 6.0 | Cumplida |
| principal | errors | 0 | ≤ 0 | Cumplida |
| dificil | recall@5 | 1.000 | ≥ 0.8 | Cumplida |
| dificil | cite_precision | 0.861 | ≥ 0.9 | Incumplida |
| dificil | abstention_accuracy | 1.000 | ≥ 0.9 | Cumplida |
| dificil | abstain_recall | 1.000 | ≥ 0.9 | Cumplida |
| dificil | latency_p95_s | 9.055 | < 6.0 | Incumplida |
| dificil | errors | 0 | ≤ 0 | Cumplida |
| solo-extra | recall@5 | 0.820 | ≥ 0.8 | Cumplida |
| solo-extra | cite_precision | 0.776 | ≥ 0.9 | Incumplida |
| solo-extra | abstention_accuracy | 0.951 | ≥ 0.9 | Cumplida |
| solo-extra | abstain_recall | – | ≥ 0.9 | No evaluable |
| solo-extra | latency_p95_s | 6.162 | < 6.0 | Incumplida |
| solo-extra | errors | 0 | ≤ 0 | Cumplida |
| security | content_answer_leaks | – | ≤ 0 | No evaluable |
| security | content_evidence_leaks | – | ≤ 0 | No evaluable |
| security | content_oracle_pass_rate | – | ≥ 1.0 | No evaluable |
| security | poison_obeyed_quarantined | 0 | ≤ 0 | Cumplida |
| security | quest_answer_leaks | – | ≤ 0 | No evaluable |
| security | quest_evidence_leaks | – | ≤ 0 | No evaluable |

## Procedencia de las mediciones

- principal: 2026-11-09T06:30:52+00:00; historical_reconstructed; `eval/results/2026-11-09_e2e_final-principal.json`.
- dificil: 2026-11-09T06:33:15+00:00; historical_reconstructed; `eval/results/2026-11-09_e2e_final-dificil.json`.
- solo-extra: 2026-11-09T06:39:10+00:00; historical_reconstructed; `eval/results/2026-11-09_e2e_final-extra.json`.
- security: 2026-11-08; bm25 / haiku; `eval/results/2026-11-08_security_guarded.json`.
- tools: 2026-11-09; bm25 / extractive; `eval/results/2026-11-09_tools.json`.

## Cómo interpretar

- **Hit-rate@5 alto con ruido alto**: llega alguna evidencia, junto con contexto irrelevante.
- **Recall de citas bajo con hit-rate@5 alto**: la evidencia disponible puede quedar fuera de las citas.
- **Apoyo léxico bajo** o **número no presente**: señal para examinar la respuesta y su respaldo, mediante revisión semántica o el juez contextual (`compare`).
- **Respondió lo no respondible** es el riesgo de seguridad de la generación; **Abstención innecesaria**, la utilidad perdida. El F1 de abstención resume ambos.
- El apoyo léxico puede penalizar paráfrasis y no certifica fidelidad. Disponer del juez contextual tampoco acredita que se haya ejecutado o validado humanamente.
