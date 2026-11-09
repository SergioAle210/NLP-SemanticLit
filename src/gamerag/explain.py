"""Explicación de una respuesta a partir de su traza (interpretabilidad: por qué respondió, por qué se abstuvo).

`explain(trace, answer)` devuelve un resumen legible y los pasos estructurados. No revela contenido bloqueado: de los
chunks descartados por los gates solo cuenta cuántos y qué control los bloqueó (nunca su título ni su texto). Es
determinista y se calcula de la traza que ya se guarda en la auditoría; la métrica `explainable_rate` del marcador mide
qué fracción de las respuestas tiene una explicación completa.
"""

from __future__ import annotations

from collections import Counter

from gamerag.pipeline import Trace
from gamerag.schemas import Answer

GATE_LABEL = {"g1_game": "otro juego", "g2_location": "contenido que aún no has desbloqueado",
              "quarantine": "texto sospechoso de contener instrucciones para el modelo",
              "provenance": "nota derivada de contenido no desbloqueado"}


def explain(trace: Trace, answer: Answer) -> dict:
    steps: list[dict] = []
    rejected = {k: v for k, v in trace.input_guards.items() if v != "ok"}
    steps.append({"stage": "entrada", "ok": not rejected, "detail": rejected or "validaciones superadas",
                  "flags": trace.input_flags})
    steps.append({"stage": "ruta", "route": trace.route, "why": trace.route_reason})
    if trace.tool:
        steps.append({"stage": "herramienta", **{k: v for k, v in trace.tool.items() if k != "params"}})
    blocked = Counter(c.blocked_by for c in trace.candidates if c.blocked_by)
    if trace.candidates:
        steps.append({"stage": "recuperación", "candidatos": len(trace.candidates),
                      "bloqueados": {GATE_LABEL.get(g, g): n for g, n in blocked.items()},
                      "entregados_al_generador": len(trace.context)})
    for i, ev in enumerate(trace.evidence, 1):
        steps.append({"stage": f"evaluación de evidencia #{i}", "suficiente": ev["sufficient"],
                      "motivo": ev.get("reason", "")})
    if trace.secondary:
        steps.append({"stage": "segunda búsqueda", "chunks_de_otras_wikis": len(trace.secondary)})
    steps.append({"stage": "salida", "guards": trace.output_guards, "citas": trace.cited})

    if trace.outcome == "rejected_input":
        why = "La pregunta no pasó las validaciones de entrada (" + ", ".join(rejected.values()) + ")."
    elif trace.outcome == "blocked_by_access":
        why = ("Todo lo relacionado con tu pregunta pertenece a contenido que aún no has desbloqueado; "
               "se retuvo para evitar spoilers.")
    elif answer.tool_used:
        why = f"Se respondió con la herramienta `{answer.tool_used}` (estado: {(trace.tool or {}).get('status')})."
        if answer.needs_human_review:
            why += " Es una acción que cambia datos: no se ejecuta sin confirmación humana."
    elif answer.abstained:
        why = "El contexto recuperado no contiene evidencia suficiente para responder; el sistema prefirió no inventar."
        if trace.evidence and not trace.evidence[-1]["sufficient"]:
            why += f" Motivo del evaluador: {trace.evidence[-1].get('reason', 'sin detalle')}."
    else:
        why = f"Respuesta fundamentada en {len(answer.sources)} fuente(s) del corpus: " + \
              ", ".join(sorted({s.source for s in answer.sources})) + "."
    if blocked:
        why += f" Se descartaron {sum(blocked.values())} fragmentos por los controles de acceso."
    complete = bool(trace.route) and bool(trace.outcome) and (bool(answer.sources) or answer.abstained
                                                              or bool(answer.tool_used) or trace.outcome != "answered")
    return {"outcome": trace.outcome, "summary": why, "steps": steps, "complete": complete}
