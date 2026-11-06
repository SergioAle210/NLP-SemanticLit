"""Pipeline de consulta: une los contratos de recuperación, acceso, generación y guardrails.

    pregunta ─► InputGuard(s) ─► Router ─┬─► Retriever ─► AccessFilter(s) ─► Generator ─┬─► OutputGuard(s) ─► Answer
                                         └─► Herramienta (filas filtradas por AccessFilter) ┘

Cada llamada devuelve también una `Trace` (cadena auditable del curso, diapositiva 16: pregunta →
filtros → candidatos → scores → contexto → generador → respuesta → citas), base del log de
auditoría y del diagnóstico de fallas. Ver docs/contracts/pipeline.md.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from pydantic import BaseModel

from gamerag.games import load_all_games
from gamerag.generation.base import ABSTAIN_MESSAGE, ExtractiveGenerator, Generator, to_source
from gamerag.guardrails.base import (
    AccessFilter,
    BasicInputGuard,
    CitationGuard,
    GameFilter,
    InputGuard,
    OutputGuard,
)
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import Hit, load_chunks
from gamerag.retrieval.factory import make_retriever
from gamerag.retrieval.hybrid import Retriever
from gamerag.schemas import Answer
from gamerag.settings import Settings
from gamerag.tools.facts import GameFacts, ToolParamError
from gamerag.tools.router import Router

log = logging.getLogger(__name__)

BLOCKED_MESSAGE = ("There is information related to this question, but it belongs to content you have not "
                   "unlocked yet. Unlock more progress to see it.")
REJECTED_MESSAGE = "The question could not be processed."


class CandidateTrace(BaseModel):
    rank: int
    chunk_id: str
    score: float
    blocked_by: str | None = None  # nombre del AccessFilter que lo bloqueó


class Trace(BaseModel):
    trace_id: str
    question: str
    game: str
    user_id: str
    role: str
    retriever: str
    generator: str
    query_variants: list[str] = []  # formulaciones usadas en la búsqueda (multi-consulta); [0] = original
    input_guards: dict[str, str] = {}  # nombre -> "ok" | motivo del bloqueo
    candidates: list[CandidateTrace] = []
    context: list[str] = []  # chunk_ids entregados al generador
    output_guards: dict[str, str] = {}
    route: str = "documents"  # decisión del router: documents | <herramienta>
    route_reason: str = ""
    tool: dict | None = None  # {name, params, status: ok|invalid_params|degraded, ...info}
    outcome: str = ""  # answered | abstained | rejected_input | blocked_by_access | rejected_output
    latency_ms: dict[str, float] = {}


class Pipeline:
    def __init__(
        self,
        retrievers: dict[str, Retriever],
        generator: Generator | None = None,
        input_guards: list[InputGuard] | None = None,
        access_filters: list[AccessFilter] | None = None,
        output_guards: list[OutputGuard] | None = None,
        top_k: int = 5,
        candidates: int = 50,
        retriever_name: str = "custom",
        router: Router | None = None,
    ):
        self.retrievers = retrievers
        self.router = router
        self.generator = generator or ExtractiveGenerator()
        self.input_guards = input_guards if input_guards is not None else [BasicInputGuard()]
        self.access_filters = access_filters if access_filters is not None else [GameFilter()]
        self.output_guards = output_guards if output_guards is not None else [CitationGuard()]
        self.top_k, self.candidates, self.retriever_name = top_k, candidates, retriever_name

    @property
    def games(self) -> list[str]:
        return sorted(self.retrievers)

    def search(self, question: str, game: str, profile: Profile) -> tuple[list[Hit], Trace]:
        """Solo las etapas 1-3 (guards de entrada, recuperación, filtros): el contexto que recibiría
        el generador, sin generar (no consume tokens del LLM). `trace.outcome` queda en
        `rejected_input`, `blocked_by_access` o `retrieved`."""
        trace = self._new_trace(question, game, profile)
        context, outcome = self._retrieve(question, game, profile, trace)
        trace.outcome = outcome or "retrieved"
        return context, trace

    def ask(self, question: str, game: str, profile: Profile) -> tuple[Answer, Trace]:
        trace = self._new_trace(question, game, profile)
        tid = trace.trace_id

        def finish(answer: Answer, outcome: str) -> tuple[Answer, Trace]:
            trace.outcome = outcome
            return answer, trace

        if not self._check_input(question, profile, trace):
            return finish(Answer(answer=REJECTED_MESSAGE, abstained=True, game=game, trace_id=tid),
                          "rejected_input")

        # Router: herramienta o documentos. Si la herramienta falla, se degrada al RAG.
        if self.router is not None:
            routed = self._run_tool(question, game, profile, trace)
            if routed is not None:
                answer, context = routed
                return finish(*self._guard_output(answer, context, profile, trace, game, tid))

        context, outcome = self._retrieve(question, game, profile, trace, check_input=False)
        if outcome == "blocked_by_access":
            return finish(Answer(answer=BLOCKED_MESSAGE, abstained=True, blocked_by_spoiler=True,
                                 game=game, trace_id=tid), outcome)

        # 4. Generación
        t = time.perf_counter()
        answer = self.generator.generate(question, context, game=game, trace_id=tid)
        trace.latency_ms["generation"] = _ms(t)

        return finish(*self._guard_output(answer, context, profile, trace, game, tid))

    def _guard_output(self, answer: Answer, context: list[Hit], profile: Profile, trace: Trace, game: str,
                      tid: str) -> tuple[Answer, str]:
        """5. Guardrails de salida (los mismos para el RAG y para las herramientas)."""
        t = time.perf_counter()
        for guard in self.output_guards:
            res = guard.check(answer, context, profile)
            trace.output_guards[guard.name] = "ok" if res.allowed else res.reason
            if not res.allowed:
                trace.latency_ms["output"] = _ms(t)
                return (Answer(answer=ABSTAIN_MESSAGE, abstained=True, needs_human_review=True, game=game,
                               trace_id=tid), "rejected_output")
        trace.latency_ms["output"] = _ms(t)
        return answer, "abstained" if answer.abstained else "answered"

    def _run_tool(self, question: str, game: str, profile: Profile,
                  trace: Trace) -> tuple[Answer, list[Hit]] | None:
        """Decide la ruta y, si es una herramienta, la ejecuta. None = seguir por el RAG."""
        t = time.perf_counter()
        route = self.router.route(question, game)
        trace.route, trace.route_reason = route.intent, route.reason
        if not route.is_tool:
            trace.latency_ms["router"] = _ms(t)
            return None
        trace.tool = {"name": route.intent, "params": route.params}

        def blocker(chunk) -> str | None:
            return next((f.name for f in self.access_filters if not f.allows(chunk, profile, game)), None)

        try:
            result = self.router.run(route, game, profile, blocker)
        except ToolParamError as e:  # parámetros fuera de rango: no se ejecuta, se informa
            trace.tool.update(status="invalid_params", error=str(e))
            trace.latency_ms["tool"] = _ms(t)
            return Answer(answer=f"I can't look that up: {e}.", abstained=True, tool_used=route.intent,
                          game=game, trace_id=trace.trace_id), []
        except Exception as e:  # degradación controlada: la herramienta falló -> RAG
            log.exception("herramienta %s falló; se degrada al RAG", route.intent)
            trace.tool.update(status="degraded", error=type(e).__name__)
            trace.route = "documents"
            trace.latency_ms["tool"] = _ms(t)
            return None
        trace.tool.update(status="ok", **result.info)
        trace.context = [h.chunk.chunk_id for h in result.hits]
        trace.latency_ms["tool"] = _ms(t)
        answer = Answer(answer=result.answer, sources=[to_source(h) for h in result.hits],
                        abstained=result.abstained, needs_human_review=result.needs_human_review,
                        tool_used=route.intent, game=game, trace_id=trace.trace_id)
        return answer, result.hits

    def _new_trace(self, question: str, game: str, profile: Profile) -> Trace:
        if game not in self.retrievers:
            raise ValueError(f"juego no disponible: {game}. Opciones: {', '.join(self.games)}")
        return Trace(trace_id=uuid.uuid4().hex, question=question, game=game, user_id=profile.user_id,
                     role=profile.role, retriever=self.retriever_name, generator=self.generator.name)

    def _check_input(self, question: str, profile: Profile, trace: Trace) -> bool:
        """1. Guardrails de entrada. False si alguno rechaza la pregunta."""
        t = time.perf_counter()
        for guard in self.input_guards:
            res = guard.check(question, profile)
            trace.input_guards[guard.name] = "ok" if res.allowed else res.reason
            if not res.allowed:
                trace.latency_ms["input"] = _ms(t)
                return False
        trace.latency_ms["input"] = _ms(t)
        return True

    def _retrieve(self, question: str, game: str, profile: Profile, trace: Trace,
                  check_input: bool = True) -> tuple[list[Hit], str | None]:
        """Etapas 1-3. Devuelve (contexto, outcome temprano o None si se puede generar)."""
        if check_input and not self._check_input(question, profile, trace):
            return [], "rejected_input"

        # 2. Recuperación (más candidatos que top_k: los filtros pueden descartar varios)
        t = time.perf_counter()
        variants = getattr(self.retrievers[game], "variants", None)
        trace.query_variants = variants(question) if variants else [question]
        hits = self.retrievers[game].search(question, k=self.candidates)
        trace.latency_ms["retrieval"] = _ms(t)

        # 3. Filtros de acceso (gates): el primero que bloquea queda registrado
        t = time.perf_counter()
        allowed: list[Hit] = []
        blocked_by_gate = False
        for h in hits:
            blocker = next((f.name for f in self.access_filters if not f.allows(h.chunk, profile, game)), None)
            trace.candidates.append(CandidateTrace(rank=h.rank, chunk_id=h.chunk.chunk_id,
                                                   score=round(h.score, 4), blocked_by=blocker))
            if blocker is None:
                allowed.append(h)
            elif blocker != GameFilter.name:
                blocked_by_gate = True
        context = [Hit(rank=i, score=h.score, chunk=h.chunk) for i, h in enumerate(allowed[: self.top_k], 1)]
        trace.context = [h.chunk.chunk_id for h in context]
        trace.latency_ms["access"] = _ms(t)

        if not context and blocked_by_gate:
            return [], "blocked_by_access"
        return context, None


def _ms(start: float) -> float:
    return round(1000 * (time.perf_counter() - start), 2)


def build_pipeline(
    settings: Settings,
    generator: Generator | None = None,
    input_guards: list[InputGuard] | None = None,
    access_filters: list[AccessFilter] | None = None,
    output_guards: list[OutputGuard] | None = None,
) -> Pipeline:
    """Arma el pipeline con la configuración servida (ADR-0009) para cada juego con chunks generados.

    Los parámetros en None usan las implementaciones por defecto (extractivo, BasicInputGuard,
    GameFilter, CitationGuard). Es el punto donde se conectan HaikuGenerator y los gates.
    """
    games = load_all_games(settings.path(settings.games_config_dir))
    retrievers: dict[str, Retriever] = {}
    facts: dict[str, GameFacts] = {}
    for game_id in games:
        path: Path = settings.path(settings.data_dir) / "processed" / game_id / f"chunks.{settings.chunker}.jsonl"
        if not path.exists():
            log.warning("sin chunks para %s (%s): corre la ingesta; el juego no estará disponible", game_id, path)
            continue
        chunks = load_chunks(path)
        retrievers[game_id] = make_retriever(settings.retriever, chunks, settings,  # type: ignore[arg-type]
                                             expand=settings.query_expansion)
        facts[game_id] = GameFacts(games[game_id], chunks)
    if not retrievers:
        raise RuntimeError("no hay chunks para ningún juego: corre `python -m gamerag.ingest.build <juego>`")
    qx = "+qx" if settings.query_expansion else ""
    return Pipeline(retrievers, generator=generator, input_guards=input_guards, access_filters=access_filters,
                    output_guards=output_guards, top_k=settings.top_k, candidates=settings.candidates,
                    retriever_name=f"{settings.retriever}{qx}/{settings.chunker}",
                    router=Router(games, facts) if settings.router else None)
