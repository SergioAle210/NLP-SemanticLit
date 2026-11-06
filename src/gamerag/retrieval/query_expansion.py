"""Transformación de consultas: corrección ortográfica + glosario del juego + multi-consulta.

Ataca el **desajuste de vocabulario** entre cómo pregunta un jugador ("attack", "money", "Level-3")
y cómo escribe la wiki ("swing the sword", "rupees", "Dungeon 3"). Sigue las estrategias del curso
(tema 08, diapositivas 211-212):

- *Query rewriting*: una variante reescrita con la terminología del juego (glosario por juego en
  config/games/<juego>.yaml, sección `query_expansion`).
- *Multi-query retrieval*: se recupera con la pregunta original **y** con la variante, y los rankings
  se fusionan con RRF. La pregunta original se conserva siempre (auditoría y para no cambiar la
  intención si la variante es mala).

La corrección ortográfica compara cada palabra desconocida con el vocabulario del corpus
("atack" -> "attack"). Ver docs/retrieval/query-expansion.md.
"""

from __future__ import annotations

import difflib
import re
from collections import Counter

from gamerag.games import QueryExpansionConfig
from gamerag.ingest.models import Chunk
from gamerag.retrieval.bm25 import Hit, index_text
from gamerag.retrieval.hybrid import Retriever, rrf_fuse

_WORD = re.compile(r"[A-Za-z][A-Za-z']+")


class QueryExpander:
    def __init__(self, config: QueryExpansionConfig, chunks: list[Chunk], min_freq: int = 2):
        self.config = config
        counts = Counter(w.lower() for c in chunks for w in _WORD.findall(index_text(c)))
        # Solo se corrigen palabras que no aparecen NI UNA vez en el corpus (si aparece, no es un error:
        # "across" no debe volverse "cross"). El destino debe aparecer al menos `min_freq` veces (evita
        # "corregir" hacia errores o rarezas del propio corpus).
        self.known = set(counts)
        self.vocab = {w for w, n in counts.items() if n >= min_freq}
        # Candidatos agrupados por primera letra: los errores de tipeo casi nunca afectan la primera
        # letra ("atack" -> "attack"), y así una palabra válida ausente del corpus no se "corrige"
        # hacia otra ("across" -> "cross").
        self._by_initial: dict[str, list[str]] = {}
        for w in sorted(self.vocab):
            self._by_initial.setdefault(w[0], []).append(w)
        # Las palabras del glosario no se corrigen: se expanden ("heal" no debe volverse "health").
        self.protected = {t.lower() for t in config.synonyms}
        self._synonyms = [(re.compile(rf"\b{re.escape(term)}\b", re.I), terms)
                          for term, terms in config.synonyms.items()]
        self._rewrites = [(re.compile(r.match, re.I), r.replace) for r in config.rewrites]

    def correct(self, query: str) -> str:
        """Corrección conservadora de errores de tipeo. Se corrige una palabra solo si:
        - tiene 5+ letras (las cortas tienen demasiados vecinos válidos: "cost" -> "coast");
        - no aparece en el corpus ni en el glosario;
        - existe una palabra del vocabulario con la misma primera letra a **distancia de edición 1**
          (una letra de más, de menos o cambiada: "atack" -> "attack", "bombz" -> "bombs")."""
        def fix(m: re.Match) -> str:
            word = m.group(0)
            low = word.lower()
            if len(low) < 5 or low in self.known or low in self.protected:
                return word
            candidates = [w for w in self._by_initial.get(low[0], []) if _edit_distance_le1(low, w)]
            if not candidates:
                return word
            best = difflib.get_close_matches(low, candidates, n=1, cutoff=0)  # el más parecido de los válidos
            return best[0]
        return _WORD.sub(fix, query)

    def rewrite(self, query: str) -> str:
        """Aplica los reemplazos de identificadores y agrega los términos del glosario."""
        text = query
        for pattern, repl in self._rewrites:
            text = pattern.sub(repl, text)
        extra: list[str] = []
        for pattern, terms in self._synonyms:
            if pattern.search(text):
                extra += [t for t in terms if t.lower() not in text.lower() and t not in extra]
        return f"{text} {' '.join(extra)}".strip() if extra else text

    def variants(self, query: str) -> list[str]:
        """[pregunta original, variante corregida y reescrita] (sin duplicados)."""
        rewritten = self.rewrite(self.correct(query))
        return [query] if rewritten == query else [query, rewritten]


def _edit_distance_le1(a: str, b: str) -> bool:
    """True si a y b difieren en a lo sumo una inserción, borrado o sustitución."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i + 1:] == b[i + 1:] if len(a) == len(b) else a[i:] == b[i + 1:]


class ExpandingRetriever:
    """Multi-consulta: recupera con cada variante (profundidad fija `candidates`) y fusiona con RRF."""

    def __init__(self, base: Retriever, expander: QueryExpander, candidates: int = 20):
        self.base, self.expander, self.candidates = base, expander, candidates
        self.retrievers = getattr(base, "retrievers", [base])

    def variants(self, query: str) -> list[str]:
        return self.expander.variants(query)

    def search(self, query: str, k: int = 5) -> list[Hit]:
        variants = self.variants(query)
        if len(variants) == 1:
            return self.base.search(query, k=k)
        return rrf_fuse([self.base.search(v, k=self.candidates) for v in variants], top_n=k)
