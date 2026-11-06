"""Configuración global leída de variables de entorno / `.env` (ver `.env.example`).

Las rutas relativas se resuelven contra `root` (por defecto, el directorio desde el que se
ejecuta: la raíz del repo en local, `/app` en Docker).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAMERAG_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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
    top_k: int = 5  # chunks que recibe el generador
    candidates: int = 50  # chunks que se recuperan antes de aplicar los filtros de acceso
    seed_profiles: Path = Path("data/seed/profiles.json")
    state_db: Path = Path("state/gamerag.sqlite3")
    games_config_dir: Path = Path("config/games")

    llm_model: str = "claude-haiku-5-5"
    # Sin prefijo GAMERAG_: es el nombre estándar que usa el SDK de Anthropic.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    log_level: str = "INFO"

    def path(self, p: Path) -> Path:
        """Resuelve una ruta de la configuración contra `root`."""
        return p if p.is_absolute() else self.root / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
