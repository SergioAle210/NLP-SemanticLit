"""Pipeline de consulta: une los contratos de recuperación, acceso, generación y guardrails.

    pregunta ─► InputGuard(s) ─► Retriever ─► AccessFilter(s) ─► Generator ─► OutputGuard(s) ─► Answer

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
from gamerag.generation.base import ABSTAIN_MESSAGE, ExtractiveGenerator, Generator
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
    input_guards: dict[str, str] = {}  # nombre -> "ok" | motivo del bloqueo
    candidates: list[CandidateTrace] = []
    context: list[str] = []  # chunk_ids entregados al generador
    output_guards: dict[str, str] = {}
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
    ):
        self.retrievers = retrievers
        self.generator = generator or ExtractiveGenerator()
        self.input_guards = input_guards if input_guards is not None else [BasicInputGuard()]
        self.access_filters = access_filters if access_filters is not None else [GameFilter()]
        self.output_guards = output_guards if output_guards is not None else [CitationGuard()]
        self.top_k, self.candidates, self.retriever_name = top_k, candidates, retriever_name

    @property
    def games(self) -> list[str]:
        return sorted(self.retrievers)

    def ask(self, question: str, game: str, profile: Profile) -> tuple[Answer, Trace]:
        if game not in self.retrievers:
            raise ValueError(f"juego no disponible: {game}. Opciones: {', '.join(self.games)}")
        trace = Trace(trace_id=uuid.uuid4().hex, question=question, game=game, user_id=profile.user_id,
                      role=profile.role, retriever=self.retriever_name, generator=self.generator.name)
        tid = trace.trace_id

        def finish(answer: Answer, outcome: str) -> tuple[Answer, Trace]:
            trace.outcome = outcome
            return answer, trace

        # 1. Guardrails de entrada
        t = time.perf_counter()
        for guard in self.input_guards:
            res = guard.check(question, profile)
            trace.input_guards[guard.name] = "ok" if res.allowed else res.reason
            if not res.allowed:
                trace.latency_ms["input"] = _ms(t)
                return finish(Answer(answer=REJECTED_MESSAGE, abstained=True, game=game, trace_id=tid),
                              "rejected_input")
        trace.latency_ms["input"] = _ms(t)

        # 2. Recuperación (más candidatos que top_k: los filtros pueden descartar varios)
        t = time.perf_counter()
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
            return finish(Answer(answer=BLOCKED_MESSAGE, abstained=True, blocked_by_spoiler=True,
                                 game=game, trace_id=tid), "blocked_by_access")

        # 4. Generación
        t = time.perf_counter()
        answer = self.generator.generate(question, context, game=game, trace_id=tid)
        trace.latency_ms["generation"] = _ms(t)

        # 5. Guardrails de salida
        t = time.perf_counter()
        for guard in self.output_guards:
            res = guard.check(answer, context, profile)
            trace.output_guards[guard.name] = "ok" if res.allowed else res.reason
            if not res.allowed:
                trace.latency_ms["output"] = _ms(t)
                return finish(Answer(answer=ABSTAIN_MESSAGE, abstained=True, needs_human_review=True,
                                     game=game, trace_id=tid), "rejected_output")
        trace.latency_ms["output"] = _ms(t)

        return finish(answer, "abstained" if answer.abstained else "answered")


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
    for game_id in games:
        path: Path = settings.path(settings.data_dir) / "processed" / game_id / f"chunks.{settings.chunker}.jsonl"
        if not path.exists():
            log.warning("sin chunks para %s (%s): corre la ingesta; el juego no estará disponible", game_id, path)
            continue
        retrievers[game_id] = make_retriever(settings.retriever, load_chunks(path), settings)  # type: ignore[arg-type]
    if not retrievers:
        raise RuntimeError("no hay chunks para ningún juego: corre `python -m gamerag.ingest.build <juego>`")
    return Pipeline(retrievers, generator=generator, input_guards=input_guards, access_filters=access_filters,
                    output_guards=output_guards, top_k=settings.top_k, candidates=settings.candidates,
                    retriever_name=f"{settings.retriever}/{settings.chunker}")
