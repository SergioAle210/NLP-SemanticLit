"""Flujo con estado (LangGraph) del pipeline de consulta.

Mismo comportamiento que `Pipeline.ask`, pero expresado como grafo explícito con un estado compartido
(`QueryState`): cada etapa es un nodo y las decisiones (rechazo, herramienta, bloqueo por acceso) son
aristas condicionales. Es la base para añadir, sin reescribir el flujo, nodos agénticos (router con LLM,
evaluador de evidencia con reintento acotado, crítico) como los de docs/arquitectura-agentica.md.

    (con evaluador, modo "always": retrieve ─► evaluate ─┬─ insuficiente ─► rewrite ─► retrieve
                                                          └─ suficiente ───► generate
     modo "on_abstain": generate ─ si se abstuvo ─► evaluate ─ insuficiente ─► rewrite ─► retrieve ─► generate
     ambos con un máximo de `max_rewrites` reintentos)

    (con planner: route ─► plan ─► retrieve×N sub-preguntas ─► unión de contextos ─► ...)

    input ─┬─ rechazado ──────────────────────────────► END
           └─► route ─┬─ herramienta ─────────────────► guard ─► END
                      └─► retrieve ─┬─ bloqueado ─────► END
                                    └─► generate ─────► guard ─► END
"""

from __future__ import annotations

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from gamerag.agents.evidence import EvidenceEvaluator
from gamerag.agents.planner import QueryPlanner
from gamerag.generation.base import Generator
from gamerag.pipeline import BLOCKED_MESSAGE, REJECTED_MESSAGE, Pipeline, Trace, _ms
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import Hit
from gamerag.schemas import Answer


class QueryState(TypedDict, total=False):
    question: str
    game: str
    profile: Profile
    trace: Trace
    context: list[Hit]
    answer: Answer
    outcome: str
    routed: bool  # una herramienta ya produjo la respuesta
    query: str  # consulta de recuperación vigente (la original o una reescritura)
    subqueries: list[str]  # sub-preguntas del planner (>1 = recuperación por separado y unión de contextos)
    attempts: int  # reescrituras ya realizadas
    sufficient: bool  # veredicto del evaluador de evidencia
    escalated: bool  # ya se hizo la busqueda secundaria (wikis extra)
    steps: list[str]  # nodos visitados (auditoría del flujo)


def _visit(state: QueryState, node: str) -> list[str]:
    return [*state.get("steps", []), node]


class GraphPipeline(Pipeline):
    """`Pipeline` cuyo `ask` se ejecuta como grafo de estados. `search` y el resto no cambian."""

    def __init__(self, *args: Any, evidence: EvidenceEvaluator | None = None, max_rewrites: int = 1,
                 evidence_mode: str = "on_abstain", planner: QueryPlanner | None = None, **kwargs: Any):
        """`evidence_mode`: "always" evalúa la evidencia antes de generar (una llamada extra por pregunta);
        "on_abstain" (por defecto) solo interviene si el generador se abstuvo: evalúa, reescribe y reintenta,
        sin costo extra en las preguntas que ya se responden."""
        super().__init__(*args, **kwargs)
        if evidence_mode not in ("always", "on_abstain"):
            raise ValueError(f"evidence_mode inválido: {evidence_mode}")
        self.evidence, self.max_rewrites, self.evidence_mode = evidence, max_rewrites, evidence_mode
        self.planner = planner
        self.graph = self._build_graph()

    # --- nodos -------------------------------------------------------------------------------

    def _n_input(self, s: QueryState) -> QueryState:
        trace, game = s["trace"], s["game"]
        if self._check_input(s["question"], s["profile"], trace):
            clean = {"question": trace.clean_question} if trace.clean_question else {}
            return {**clean, "steps": _visit(s, "input")}
        return {"answer": Answer(answer=REJECTED_MESSAGE, abstained=True, game=game, trace_id=trace.trace_id),
                "outcome": "rejected_input", "steps": _visit(s, "input")}

    def _n_route(self, s: QueryState) -> QueryState:
        routed = None
        if self.router is not None:
            routed = self._run_tool(s["question"], s["game"], s["profile"], s["trace"])
        if routed is None:
            return {"routed": False, "steps": _visit(s, "route")}
        answer, context = routed
        return {"routed": True, "answer": answer, "context": context, "steps": _visit(s, "route")}

    def _n_plan(self, s: QueryState) -> QueryState:
        t = time.perf_counter()
        queries = self.planner.plan(s["question"])
        s["trace"].latency_ms["planner"] = _ms(t)
        return {"subqueries": queries, "steps": _visit(s, "plan")}

    def _merge(self, per_sub: list[list[Hit]]) -> list[Hit]:
        """Une los contextos de las sub-preguntas intercalando por rango, sin duplicados."""
        cap = self.top_k + 2 * (len(per_sub) - 1)
        seen: set[str] = set()
        merged: list[Hit] = []
        for rank in range(max(map(len, per_sub), default=0)):
            for ctx in per_sub:
                if rank < len(ctx) and ctx[rank].chunk.chunk_id not in seen and len(merged) < cap:
                    seen.add(ctx[rank].chunk.chunk_id)
                    merged.append(ctx[rank])
        return [Hit(rank=i, score=h.score, chunk=h.chunk) for i, h in enumerate(merged, 1)]

    def _n_retrieve(self, s: QueryState) -> QueryState:
        trace = s["trace"]
        subs = s.get("subqueries") or []
        if len(subs) > 1 and "query" not in s:  # una reescritura del evaluador reemplaza la descomposición
            per_sub, outcomes = [], []
            for q in subs:
                ctx, out = self._retrieve(q, s["game"], s["profile"], trace, check_input=False)
                per_sub.append(ctx)
                outcomes.append(out)
            context = self._merge(per_sub)
            trace.subqueries = [{"query": q, "context": [h.chunk.chunk_id for h in c]}
                                for q, c in zip(subs, per_sub, strict=True)]
            trace.context = [h.chunk.chunk_id for h in context]
            outcome = "blocked_by_access" if not context and "blocked_by_access" in outcomes else None
        else:
            context, outcome = self._retrieve(s.get("query", s["question"]), s["game"], s["profile"], trace,
                                              check_input=False)
        if outcome == "blocked_by_access":
            ans = Answer(answer=BLOCKED_MESSAGE, abstained=True, blocked_by_spoiler=True, game=s["game"],
                         trace_id=trace.trace_id)
            return {"answer": ans, "outcome": outcome, "context": [], "steps": _visit(s, "retrieve")}
        return {"context": context, "steps": _visit(s, "retrieve")}

    def _n_evaluate(self, s: QueryState) -> QueryState:
        t = time.perf_counter()
        query = s.get("query", s["question"])
        v = self.evidence.evaluate(s["question"], s["context"])
        s["trace"].evidence.append({"sufficient": v.sufficient, "reason": v.reason, "rewrite": v.rewrite,
                                    "query": query})
        s["trace"].latency_ms["evidence"] = round(s["trace"].latency_ms.get("evidence", 0.0) + _ms(t), 2)
        return {"sufficient": v.sufficient, "steps": _visit(s, "evaluate")}

    def _n_secondary(self, s: QueryState) -> QueryState:
        """Segunda busqueda en las wikis extra (con la reescritura del evaluador si la hay), agregada al contexto."""
        trace = s["trace"]
        rewrite = trace.evidence[-1]["rewrite"] if trace.evidence else ""
        extra, _ = self._retrieve(rewrite or s["question"], s["game"], s["profile"], trace, check_input=False,
                                  retriever=self.secondary[s["game"]], top_k=self.secondary_k)
        have = {h.chunk.chunk_id for h in s["context"]}
        merged = (list(extra) if self.secondary_replace
                  else [*s["context"], *[h for h in extra if h.chunk.chunk_id not in have]])
        merged = [Hit(rank=i, score=h.score, chunk=h.chunk) for i, h in enumerate(merged, 1)]
        trace.context = [h.chunk.chunk_id for h in merged]
        trace.secondary = [h.chunk.chunk_id for h in merged if h.chunk.origin != "strategywiki"]
        return {"context": merged, "escalated": True, "steps": _visit(s, "secondary")}

    def _n_rewrite(self, s: QueryState) -> QueryState:
        # Nueva recuperación: se reinician candidatos y variantes para que la trace refleje el último intento.
        s["trace"].candidates = []
        rewrite = s["trace"].evidence[-1]["rewrite"]
        return {"query": rewrite, "attempts": s.get("attempts", 0) + 1, "steps": _visit(s, "rewrite")}

    def _n_generate(self, s: QueryState) -> QueryState:
        t = time.perf_counter()
        answer = self.generator.generate(s["question"], s["context"], game=s["game"],
                                         trace_id=s["trace"].trace_id)
        s["trace"].latency_ms["generation"] = _ms(t)
        return {"answer": answer, "steps": _visit(s, "generate")}

    def _n_guard(self, s: QueryState) -> QueryState:
        answer, outcome = self._guard_output(s["answer"], s["context"], s["profile"], s["trace"], s["game"],
                                             s["trace"].trace_id)
        return {"answer": answer, "outcome": outcome, "steps": _visit(s, "guard")}

    # --- aristas -----------------------------------------------------------------------------

    @staticmethod
    def _after_input(s: QueryState) -> str:
        return "end" if s.get("outcome") == "rejected_input" else "route"

    def _after_route(self, s: QueryState) -> str:
        if s.get("routed"):
            return "guard"
        return "plan" if self.planner is not None else "retrieve"

    def _after_retrieve(self, s: QueryState) -> str:
        if s.get("outcome") == "blocked_by_access":
            return "end"
        return "evaluate" if self.evidence is not None and self.evidence_mode == "always" else "generate"

    def _after_generate(self, s: QueryState) -> str:
        retry = (self.evidence is not None and self.evidence_mode == "on_abstain" and s["answer"].abstained
                 and s.get("attempts", 0) < self.max_rewrites)
        return "evaluate" if retry else "guard"

    def _after_evaluate(self, s: QueryState) -> str:
        insufficient = not s.get("sufficient", True)
        if insufficient and self.secondary.get(s["game"]) and not s.get("escalated"):
            return "secondary"
        can_retry = s.get("attempts", 0) < self.max_rewrites and bool(s["trace"].evidence[-1]["rewrite"])
        if insufficient and can_retry:
            return "rewrite"
        return "generate" if self.evidence_mode == "always" else "guard"

    def _build_graph(self):
        g = StateGraph(QueryState)
        g.add_node("input", self._n_input)
        g.add_node("route", self._n_route)
        g.add_node("plan", self._n_plan)
        g.add_node("retrieve", self._n_retrieve)
        g.add_node("evaluate", self._n_evaluate)
        g.add_node("rewrite", self._n_rewrite)
        g.add_node("secondary", self._n_secondary)
        g.add_node("generate", self._n_generate)
        g.add_node("guard", self._n_guard)
        g.add_edge(START, "input")
        g.add_conditional_edges("input", self._after_input, {"end": END, "route": "route"})
        g.add_conditional_edges("route", self._after_route, {"guard": "guard", "plan": "plan", "retrieve": "retrieve"})
        g.add_edge("plan", "retrieve")
        g.add_conditional_edges("retrieve", self._after_retrieve,
                                {"end": END, "evaluate": "evaluate", "generate": "generate"})
        g.add_conditional_edges("evaluate", self._after_evaluate,
                                {"rewrite": "rewrite", "secondary": "secondary", "generate": "generate",
                                 "guard": "guard"})
        g.add_edge("secondary", "generate")
        g.add_edge("rewrite", "retrieve")
        g.add_conditional_edges("generate", self._after_generate, {"evaluate": "evaluate", "guard": "guard"})
        g.add_edge("guard", END)
        return g.compile()

    # --- API ---------------------------------------------------------------------------------

    def ask(self, question: str, game: str, profile: Profile) -> tuple[Answer, Trace]:
        state = self.run(question, game, profile)
        return state["answer"], state["trace"]

    def run(self, question: str, game: str, profile: Profile) -> QueryState:
        """Ejecuta el grafo y devuelve el estado final (incluye `steps`, útil en pruebas y diagnóstico)."""
        trace = self._new_trace(question, game, profile)
        state: QueryState = self.graph.invoke({"question": question, "game": game, "profile": profile,
                                               "trace": trace, "steps": []})
        state["trace"].outcome = state["outcome"]
        state["trace"].cited = [src.chunk_id for src in state["answer"].sources]
        return state


def graph_from(pipeline: Pipeline, **kw: Any) -> GraphPipeline:
    """Envuelve un `Pipeline` ya armado (mismos retrievers, guards, router y generador)."""
    gen: Generator = pipeline.generator
    kw = {"secondary": pipeline.secondary, "secondary_k": pipeline.secondary_k,
          "secondary_replace": pipeline.secondary_replace, **kw}  # los kw pueden sobrescribir
    return GraphPipeline(pipeline.retrievers, generator=gen, input_guards=pipeline.input_guards,
                         access_filters=pipeline.access_filters, output_guards=pipeline.output_guards,
                         top_k=pipeline.top_k, candidates=pipeline.candidates,
                         retriever_name=pipeline.retriever_name, router=pipeline.router, **kw)
