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


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for tok in _TOKEN.findall(text.lower()):
        tok = re.sub(r"'s$", "", tok)
        if "-" in tok:
            tokens.append(tok)
            tokens += [p for p in tok.split("-") if p and p not in STOPWORDS]
        elif tok not in STOPWORDS:
            tokens.append(tok.replace("'", ""))
    return tokens
