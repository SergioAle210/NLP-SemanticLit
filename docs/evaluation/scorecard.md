# Marcador del sistema

Generado por `python -m gamerag.evaluation.scorecard` desde los resultados vigentes (`eval/scorecard_manifest.json`). Todas las métricas salen de JSON ya generados (sin llamadas a la API). Definiciones en [diagnostics.py](../../src/gamerag/evaluation/diagnostics.py).

| Métrica | principal | dificil | solo-extra |
| --- | ---: | ---: | ---: |
| n (casos) | 54 | 21 | 61 |
| casos con evaluación de recuperación | 49 | 18 | 61 |
| **Recuperación** | | | |
| Recall@5 | 0.959 | 1.000 | 0.820 |
| MRR | 0.695 | 0.944 | 0.685 |
| nDCG@5 | 0.765 | 0.955 | 0.720 |
| Cobertura de evidencia | 0.949 | 0.917 | 0.820 |
| Ruido en el contexto | 0.747 | 0.778 | 0.836 |
| Redundancia | 0.100 | 0.107 | 0.080 |
| **Atribución y fidelidad** | | | |
| Recall de citas | 0.948 | 0.917 | 0.862 |
| Apoyo léxico (groundedness) | 0.743 | 0.810 | 0.817 |
| Oraciones sin apoyo | 0.147 | 0.102 | 0.050 |
| Respuestas con número no presente | 0.160 | 0.00000 | 0.00000 |
| **Abstención y calibración** | | | |
| Precisión de abstención | 0.750 | 1.000 | – |
| Recall de abstención | 0.600 | 1.000 | – |
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
| Respuestas generadas con contenido bloqueado (sondas de spoiler) | 0 |
| Chunks bloqueados entregados al LLM | 0 |
| Documentos envenenados obedecidos (con cuarentena) | 0 |
| Preguntas legítimas rechazadas (falsos positivos) | 0 |
| Casos de herramientas cumplidos | 1 |
| Selección de herramienta | 1 |
| Falso disparo del router en bancos de documentos | 0 |

## Regresiones frente a la línea base

Ninguna.

## Cómo interpretar

- **Recall@5 alto con Ruido alto**: la evidencia llega, pero el generador paga tokens por contexto irrelevante.
- **Recall de citas bajo con Recall@5 alto**: el modelo recibe la evidencia pero cita otra cosa (atribución débil).
- **Apoyo léxico bajo** o **número no presente**: posible alucinación; confirmar con el juez LLM (`compare`).
- **Respondió lo no respondible** es el riesgo de seguridad de la generación; **Abstención innecesaria**, la utilidad perdida. El F1 de abstención resume ambos.
- Una métrica léxica no sustituye al juez: el apoyo léxico no entiende paráfrasis. Sirve para detectar cambios, no para certificar fidelidad.
