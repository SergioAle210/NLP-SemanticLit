"""Configuración global leída de variables de entorno / `.env` (ver `.env.example`).

Las rutas relativas se resuelven contra `root` (por defecto, el directorio desde el que se
ejecuta: la raíz del repo en local, `/app` en Docker).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAMERAG_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # base: recuperacion hibrida + generador extractivo (sin LLM, sin costo).
    # full: la configuracion evaluada del sistema (grafo + Haiku + evaluador de evidencia + segunda busqueda con indice
    # mezclado); requiere ANTHROPIC_API_KEY, sin ella se queda en `base`. Los campos fijados explicitamente ganan.
    profile: str = "base"

    root: Path = Field(default_factory=Path.cwd)
    data_dir: Path = Path("data")
    index_dir: Path = Path("data/index")
    models_dir: Path = Path("models")  # caché de modelos de Hugging Face (fuera de git)
    # Clave de gamerag.retrieval.embeddings.MODELS. Provisional: mejor variante híbrida con chunking fijo
    # (docs/evaluation/results.md); se confirma con chunking estructural.
    embedding_model: str = "e5-small-multi"
    # Configuración de recuperación servida por el pipeline (ADR-0009).
    retriever: str = "hybrid"  # bm25 | dense | hybrid
    chunker: str = "structural"  # sufijo de data/processed/<juego>/chunks.<chunker>.jsonl
    query_expansion: bool = True  # multi-consulta con corrección ortográfica + glosario del juego
    tool_timeout_s: float = 5.0  # limite de tiempo por herramienta; al excederlo se degrada al RAG
    rate_limit_per_min: int = 60  # solicitudes /ask y /search por usuario y minuto (0 = sin limite)
    router: bool = True  # router de intención + herramientas (docs/tools/README.md)
    top_k: int = 5  # chunks que recibe el generador
    candidates: int = 50  # chunks que se recuperan antes de aplicar los filtros de acceso
    seed_profiles: Path = Path("data/seed/profiles.json")
    state_db: Path = Path("state/gamerag.sqlite3")
    games_config_dir: Path = Path("config/games")

    security_guards: bool = True  # inyeccion, PII redactada, cuarentena de chunks y fuga del prompt
    spoiler_gates: bool = True  # G2: oculta contenido de ubicaciones aún no alcanzadas (desactivar solo para medir)
    use_graph: bool = False  # ejecutar la consulta como grafo de estados (LangGraph, gamerag/graph.py)
    only_games: list[str] = []  # si no esta vacia, solo se arman estos juegos (evaluaciones por juego)
    secondary_search: bool = False  # wikis extra como segunda busqueda si la evidencia es insuficiente (usa -multi)
    secondary_mode: str = "append"  # append: suma chunks extra; mixed: indice mezclado reemplaza el contexto
    secondary_franchise: bool = False  # incluir en la segunda busqueda las fuentes de toda la saga (scope: franchise)
    secondary_k: int = 3  # chunks que la busqueda secundaria agrega al contexto
    planner: bool = False  # descomposición de consulta en sub-preguntas (requiere use_graph y API key)
    memory_notes: bool = False  # indexar las notas de data/memory/<juego>/notes.jsonl junto a los chunks
    memory_dir: Path = Path("data/memory")
    evidence_eval: bool = False  # evaluador de evidencia + reescritura (requiere use_graph y API key)
    evidence_mode: str = "on_abstain"  # on_abstain (solo si el generador se abstiene) | always
    max_rewrites: int = 1  # tope de reintentos de recuperación por consulta
    generator: str = "extractive"  # extractive | haiku (haiku degrada al extractivo si el LLM falla)
    llm_model: str = "claude-haiku-5-5"
    # Sin prefijo GAMERAG_: es el nombre estándar que usa el SDK de Anthropic.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    # Control de costo del LLM (gamerag/llm.py). Precios: USD por millón de tokens, estimación conservadora
    # (verificar en la consola de Anthropic). El tope es del proyecto entero, acumulado entre corridas.
    llm_budget_usd: float = 15.0
    llm_run_budget_usd: float = 1.0
    llm_max_tokens: int = 1024  # techo de salida por llamada, pida lo que pida el código
    llm_price_input: float = 0.10  # Haiku 5.5, prompts <100K tokens (tabla de precios de la API, 2026-10)
    llm_price_output: float = 0.50
    llm_cache: bool = True
    llm_offline: bool = False  # solo caché: repetir evaluaciones y correr tests sin gastar
    llm_cache_dir: Path = Path("state/llm_cache")
    llm_usage_db: Path = Path("state/llm_usage.sqlite3")

    log_level: str = "INFO"

    @model_validator(mode="after")
    def _apply_profile(self) -> Settings:
        if self.profile not in ("base", "full"):
            raise ValueError(f"profile invalido: {self.profile} (base | full)")
        if self.profile == "full" and self.anthropic_api_key is not None:
            preset = {"generator": "haiku", "use_graph": True, "evidence_eval": True, "evidence_mode": "on_abstain",
                      "secondary_search": True, "secondary_mode": "mixed", "secondary_k": 5}
            for name, value in preset.items():
                if name not in self.model_fields_set:
                    object.__setattr__(self, name, value)
        return self

    def path(self, p: Path) -> Path:
        """Resuelve una ruta de la configuración contra `root`."""
        return p if p.is_absolute() else self.root / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
