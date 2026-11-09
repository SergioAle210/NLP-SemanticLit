"""Contrato del chunk: la unidad que se indexa, se recupera y se cita.

Incluye los campos mínimos exigidos por el curso (§5.3: text, source, page, chunk_id, version)
más metadatos de trazabilidad y de ubicación en el juego (base de los gates de spoilers).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Location(BaseModel):
    """Dónde ocurre el contenido dentro del juego. None = contenido general (sin restricción)."""

    quest: str | None = None  # Zelda: "first" | "second"
    level: int | None = None  # Zelda: mazmorra 1-9
    act: int | None = None  # Ninja Gaiden: acto 1-6
    stage: str | None = None  # Ninja Gaiden: "2-3"
    # Sin ubicación asignada en una fuente que no la trae en sus títulos (Wikipedia, wikis de fans): solo la ven
    # perfiles sin restricción hasta que se etiquete. Evita que contenido de cualquier punto del juego cuente
    # como "general" y se filtre a un jugador que apenas empieza.
    restricted: bool = False


class Chunk(BaseModel):
    # --- mínimos del curso ---
    chunk_id: str
    text: str
    source: str = Field(description="Título de la página de la wiki")
    page: int = Field(ge=0, description="Índice de la sección donde empieza el chunk")
    version: str = Field(description="Versión documental: revid de la página")
    # --- trazabilidad ---
    url: str
    section: str = Field(description="Sección donde empieza el chunk")
    sections: list[str] = Field(description="Todas las secciones que abarca")
    hash: str = Field(description="sha256 del texto (detecta cambios entre ingestas)")
    chunker: str = Field(description="Estrategia y parámetros de chunking")
    n_words: int
    lang: str = "en"
    # --- acceso ---
    game: str
    location: Location = Location()
    # --- memoria (notas generadas por `gamerag.dream`) ---
    origin: str = "strategywiki"  # wiki de la que sale el chunk (las extra van a la busqueda secundaria)
    kind: str = "source"  # "source" (wiki) | "note" (derivada, verificada contra sus fuentes)
    derived_from: list[str] = []  # chunk_ids de los que sale una nota (su acceso depende de todos ellos)
