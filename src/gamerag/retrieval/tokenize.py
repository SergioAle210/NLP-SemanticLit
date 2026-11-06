"""Tokenización para la búsqueda léxica (BM25).

Decisiones (ver docs/retrieval/bm25.md):
- Minúsculas; tokens alfanuméricos.
- Los identificadores con guion se conservan completos **y** por partes:
  "Level-4" -> ["level-4", "level", "4"]; "D-4" -> ["d-4", "d", "4"].
  Así coincide tanto la búsqueda exacta ("Level-4") como la suelta ("level 4").
- Posesivos: "link's" -> "link".
- Stopwords: lista corta en inglés (palabras funcionales). Sin stemming en la línea base.
"""

from __future__ import annotations

import re

STOPWORDS = frozenset("""
a an the and or but if then else of to in on at by for with from as into onto about over under
is are was were be been being am do does did done have has had having
i me my we our you your he him his she her it its they them their this that these those
what which who whom whose where when why how can could should would will shall may might must
not no so than too very just only also there here up down out off again
""".split())

_TOKEN = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")
_NUMBER = re.compile(r"\d+(?:-\d+)?")  # "1", "2-3"
_WORD = re.compile(r"[a-z]+")


def tokenize(text: str, phrases: bool = True) -> list[str]:
    """Tokens para BM25. Con `phrases`, cada palabra seguida de un número agrega además un token de
    frase ("level 1" y "Level-1" -> "level_1"; "stage 2-3" -> "stage_2-3"). BM25 es una bolsa de
    palabras: sin ese token, "level 1" coincide con cualquier texto que tenga "level" y algún "1"
    ("Quest 1/Dungeon 3" contiene "dungeon" y "1"). Ver docs/retrieval/bm25.md."""
    raw = [re.sub(r"'s$", "", t) for t in _TOKEN.findall(text.lower())]
    tokens: list[str] = []
    for i, tok in enumerate(raw):
        if "-" in tok:
            tokens.append(tok)
            tokens += [p for p in tok.split("-") if p and p not in STOPWORDS]
            head, _, tail = tok.partition("-")
            if phrases and _WORD.fullmatch(head) and head not in STOPWORDS and _NUMBER.fullmatch(tail):
                tokens.append(f"{head}_{tail}")  # "level-1" -> "level_1"
        elif tok not in STOPWORDS:
            tokens.append(tok.replace("'", ""))
            nxt = raw[i + 1] if i + 1 < len(raw) else ""
            if phrases and _WORD.fullmatch(tok) and _NUMBER.fullmatch(nxt):
                tokens.append(f"{tok}_{nxt}")  # "level 1" -> "level_1"
    return tokens
