"""API HTTP (FastAPI) sobre el pipeline. Es el backend único: lo consumen la interfaz y la evaluación.

Uso (desarrollo):
    uv run uvicorn gamerag.api:app --reload
    -> documentación interactiva (OpenAPI) en http://127.0.0.1:8000/docs

Control de acceso de demo: cada request indica `user_id` de uno de los perfiles sembrados (sin login,
ADR-0004). Los endpoints administrativos exigen un perfil con rol `admin`.
Ver docs/api/README.md.

Nota: este módulo NO usa `from __future__ import annotations`. Con esa importación las anotaciones
son texto y FastAPI no puede resolver los alias de dependencias definidos dentro de `create_app`
(los trataría como parámetros de query y respondería 422).
"""

import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from gamerag import __version__
from gamerag.explain import explain
from gamerag.games import GameConfig, load_all_games
from gamerag.pipeline import Pipeline, Trace, build_pipeline
from gamerag.progress.models import Profile, load_profiles
from gamerag.schemas import Answer
from gamerag.settings import Settings, get_settings
from gamerag.store import Store

log = logging.getLogger(__name__)

USER_ID = Field(pattern=r"^[a-z0-9_]+$", max_length=64)


# --- modelos de request/response --------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    game: str = Field(pattern=r"^[a-z0-9_]+$")
    user_id: str = USER_ID
    include_trace: bool = True


class AskResponse(BaseModel):
    answer: Answer
    trace: Trace | None = None
    explanation: dict | None = None  # por que respondio / se abstuvo (gamerag/explain.py); con include_trace


class SearchHit(BaseModel):
    rank: int
    score: float
    chunk_id: str
    source: str
    section: str
    url: str
    text: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    trace: Trace


class GameInfo(BaseModel):
    game_id: str
    title: str
    year: int
    progress_model: str
    levels: list[int] | None = None
    quests: list[str] | None = None
    stages: list[str] | None = None
    available: bool  # hay índice cargado para este juego


class HealthResponse(BaseModel):
    status: str
    version: str
    games: list[str]
    retriever: str
    generator: str


# --- aplicación -------------------------------------------------------------------------------

def create_app(settings: Settings | None = None, pipeline: Pipeline | None = None,
               store: Store | None = None) -> FastAPI:
    """Fábrica de la app. En producción construye todo desde `settings`; los tests inyectan un
    pipeline y un store livianos."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = settings or get_settings()
        games = load_all_games(s.path(s.games_config_dir))
        st = store or Store(s.path(s.state_db))
        st.seed_profiles(load_profiles(s.path(s.seed_profiles), games))
        if s.audit_retention_days:  # retencion: al arrancar se descartan las trazas vencidas
            st.purge_traces(s.audit_retention_days)
        # El pipeline se construye una sola vez: cargar el modelo de embeddings toma segundos.
        app.state.pipeline = pipeline or build_pipeline(s)
        app.state.store, app.state.games, app.state.settings = st, games, s
        log.info("API lista: juegos=%s", app.state.pipeline.games)
        yield
        if store is None:
            st.close()

    app = FastAPI(title="GameRAG API", version=__version__, lifespan=lifespan,
                  description="RAG sobre juegos retro de NES con protección de spoilers (CC3103, UVG).")

    recent: dict[str, deque[float]] = defaultdict(deque)  # solicitudes por usuario en el ultimo minuto

    def rate_limit(request: Request, user_id: str) -> None:
        """Limite de alcance por usuario (ventana deslizante de 60 s) sobre /ask y /search; 0 = sin limite."""
        limit = request.app.state.settings.rate_limit_per_min
        if not limit:
            return
        now, window = time.monotonic(), recent[user_id]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(429, f"demasiadas solicitudes ({limit} por minuto); espera un momento")
        window.append(now)

    def get_pipeline(request: Request) -> Pipeline:
        return request.app.state.pipeline

    def get_store(request: Request) -> Store:
        return request.app.state.store

    def get_games(request: Request) -> dict[str, GameConfig]:
        return request.app.state.games

    def profile_or_404(store: Store, user_id: str) -> Profile:
        profile = store.get_profile(user_id)
        if profile is None:
            raise HTTPException(404, f"perfil desconocido: {user_id}")
        return profile

    def require_admin(store: Store, user_id: str) -> Profile:
        profile = profile_or_404(store, user_id)
        if profile.role != "admin":
            raise HTTPException(403, "requiere un perfil con rol admin")
        return profile

    def check_game(pipe: Pipeline, game: str) -> None:
        if game not in pipe.retrievers:
            raise HTTPException(404, f"juego no disponible: {game}. Opciones: {', '.join(pipe.games)}")

    PipelineDep = Annotated[Pipeline, Depends(get_pipeline)]
    StoreDep = Annotated[Store, Depends(get_store)]
    GamesDep = Annotated[dict[str, GameConfig], Depends(get_games)]

    @app.get("/health", response_model=HealthResponse, tags=["sistema"])
    def health(pipe: PipelineDep) -> HealthResponse:
        return HealthResponse(status="ok", version=__version__, games=pipe.games,
                              retriever=pipe.retriever_name, generator=pipe.generator.name)

    @app.get("/games", response_model=list[GameInfo], tags=["catálogo"])
    def list_games(pipe: PipelineDep, games: GamesDep) -> list[GameInfo]:
        return [GameInfo(game_id=g.game_id, title=g.title, year=g.year, progress_model=g.progress_model.value,
                         levels=g.levels, quests=g.quests, stages=g.stages, available=g.game_id in pipe.retrievers)
                for g in games.values()]

    @app.get("/profiles", response_model=list[Profile], tags=["perfiles"])
    def list_profiles(store: StoreDep) -> list[Profile]:
        return store.list_profiles()

    @app.get("/profiles/{user_id}", response_model=Profile, tags=["perfiles"])
    def get_profile(user_id: str, store: StoreDep) -> Profile:
        return profile_or_404(store, user_id)

    @app.post("/ask", response_model=AskResponse, tags=["consulta"])
    def ask(req: AskRequest, request: Request, pipe: PipelineDep, store: StoreDep) -> AskResponse:
        """Pregunta → respuesta con citas (contrato §11) + traza. Cada consulta queda en el log de auditoría."""
        check_game(pipe, req.game)
        profile = profile_or_404(store, req.user_id)
        rate_limit(request, req.user_id)
        answer, trace = pipe.ask(req.question, req.game, profile)
        store.log_trace(trace)
        return AskResponse(answer=answer, trace=trace if req.include_trace else None,
                           explanation=explain(trace, answer) if req.include_trace else None)

    @app.post("/search", response_model=SearchResponse, tags=["consulta"])
    def search(req: AskRequest, request: Request, pipe: PipelineDep, store: StoreDep) -> SearchResponse:
        """Solo recuperación + filtros: el contexto que recibiría el generador (sin generar, sin tokens)."""
        check_game(pipe, req.game)
        profile = profile_or_404(store, req.user_id)
        rate_limit(request, req.user_id)
        context, trace = pipe.search(req.question, req.game, profile)
        hits = [SearchHit(rank=h.rank, score=round(h.score, 4), chunk_id=h.chunk.chunk_id, source=h.chunk.source,
                          section=h.chunk.section, url=h.chunk.url, text=h.chunk.text) for h in context]
        return SearchResponse(hits=hits, trace=trace)

    @app.get("/audit", tags=["admin"])
    def audit(store: StoreDep, user_id: Annotated[str, Query(pattern=r"^[a-z0-9_]+$")],
              limit: Annotated[int, Query(ge=1, le=200)] = 20) -> list[dict]:
        """Últimas trazas del log de auditoría (preguntas con PII redactada). Requiere rol admin."""
        require_admin(store, user_id)
        return store.recent_traces(limit)

    @app.get("/scorecard", tags=["sistema"])
    def scorecard(request: Request) -> dict:
        """Marcador vigente de evaluación (métricas agregadas, sin datos de usuarios)."""
        s: Settings = request.app.state.settings
        path = s.path(Path("eval/results/scorecard_latest.json"))
        if not path.exists():
            raise HTTPException(404, "no hay marcador: corre python -m gamerag.evaluation.scorecard")
        return json.loads(path.read_text(encoding="utf-8"))

    @app.post("/admin/reset-profiles", tags=["admin"])
    def reset_profiles(store: StoreDep, games: GamesDep, request: Request,
                       user_id: Annotated[str, Query(pattern=r"^[a-z0-9_]+$")]) -> dict:
        """Restablece los perfiles sembrados (para repetir la demo y la evaluación). Requiere rol admin."""
        require_admin(store, user_id)
        s: Settings = request.app.state.settings
        n = store.seed_profiles(load_profiles(s.path(s.seed_profiles), games), overwrite=True)
        return {"reset": n}

    @app.post("/admin/purge-audit", tags=["admin"])
    def purge_audit(store: StoreDep, request: Request,
                    user_id: Annotated[str, Query(pattern=r"^[a-z0-9_]+$")]) -> dict:
        """Aplica la politica de retencion (`audit_retention_days`): borra trazas mas antiguas. Requiere rol admin."""
        require_admin(store, user_id)
        days = request.app.state.settings.audit_retention_days
        return {"retention_days": days, "purged": store.purge_traces(days) if days else 0}

    return app


app = create_app()
