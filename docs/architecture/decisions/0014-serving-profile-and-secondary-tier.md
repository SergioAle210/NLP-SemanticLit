# ADR-0014: Perfil de servicio `full`, segunda búsqueda por niveles y alcance de las fuentes

Estado: aceptada (2026-11-09)

## Contexto

Tras la ablación agéntica (`docs/evaluation/agentic-ablation.md`) hay varias piezas opcionales (grafo, Haiku, evaluador de
evidencia, planificador, notas de memoria, segunda búsqueda). Mezclar todas las wikis en un índice degrada el banco
principal (Recall@5 0.97 → 0.69); el evaluador solo ayuda con BM25; las notas de memoria y el planificador no mostraron
ganancia medible en el banco actual.

## Decisión

- Dos perfiles (`GAMERAG_PROFILE`): `base` (híbrido + extractivo, sin LLM ni costo; por defecto, el de CI y tests) y `full`
  (grafo + Haiku + evaluador `on_abstain` + segunda búsqueda `mixed` con k=5). `full` sin `ANTHROPIC_API_KEY` se queda en
  `base`. Un campo fijado explícitamente gana al perfil.
- El corpus principal (StrategyWiki) es la primera búsqueda. Las wikis extra solo se consultan **cuando el evaluador juzga
  insuficiente la evidencia**, una sola vez, con un índice que mezcla todas las wikis; el contexto se reemplaza por sus 5
  mejores chunks. Los gates (G1, G2, procedencia, cuarentena) aplican igual al segundo nivel.
- Las fuentes con `scope: franchise` (Zeldapedia, ZeldaWiki) mezclan varios títulos y se excluyen del segundo nivel.
- Planificador y notas de memoria quedan **apagados** en `full` hasta demostrar ganancia (resultados negativos documentados).
- El tope de gasto por corrida es por proceso; el tope total del proyecto es acumulado.

## Consecuencias

- La segunda búsqueda eleva la correctitud en contenido que solo está en las wikis extra (0.04 → 0.84) sin cambiar el
  banco principal. No alcanza al índice mezclado siempre (0.89 en el banco de 84) pero no degrada lo ya resuelto.
- El 17 % de las preguntas que el generador responde con confianza desde contexto irrelevante no escalan (límite del
  modo `on_abstain`); el modo `always` cuesta una llamada extra por pregunta y no se adopta.
