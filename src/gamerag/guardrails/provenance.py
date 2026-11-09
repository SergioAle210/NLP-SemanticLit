"""Gate de procedencia para las notas de memoria.

Una nota (`Chunk.kind == "note"`) es un resumen derivado de varios chunks. Para que no pueda filtrar lo
que sus fuentes no dejarían ver, se permite solo si **todas** sus fuentes pasan **todos** los demás
filtros de acceso para ese perfil. Así el acceso de una nota es el más restrictivo de sus fuentes sin
copiar etiquetas (que podrían quedar desactualizadas) y funciona con cualquier gate presente o futuro
(G2-G4) sin código adicional. Una fuente desconocida se trata como bloqueada (fallo cerrado).
"""

from __future__ import annotations

from gamerag.guardrails.base import AccessFilter
from gamerag.ingest.models import Chunk
from gamerag.progress.models import Profile


class ProvenanceFilter:
    name = "provenance"

    def __init__(self, chunks_by_id: dict[str, Chunk], base_filters: list[AccessFilter]):
        self.chunks_by_id, self.base_filters = chunks_by_id, base_filters

    def allows(self, chunk: Chunk, profile: Profile, game: str) -> bool:
        if chunk.kind != "note":
            return True
        if not chunk.derived_from:
            return False
        for cid in chunk.derived_from:
            src = self.chunks_by_id.get(cid)
            if src is None or not all(f.allows(src, profile, game) for f in self.base_filters):
                return False
        return True


def leaked_notes(context_chunks: list[Chunk], chunks_by_id: dict[str, Chunk], base_filters: list[AccessFilter],
                 profile: Profile, game: str) -> list[str]:
    """Métrica de fuga: ids de notas presentes en un contexto cuyas fuentes el perfil no podría ver."""
    return [c.chunk_id for c in context_chunks if c.kind == "note"
            and not ProvenanceFilter(chunks_by_id, base_filters).allows(c, profile, game)]
