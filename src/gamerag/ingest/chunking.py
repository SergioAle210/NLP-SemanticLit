"""Chunking de tamaño fijo (línea base, fase 2).

Ventana deslizante de N palabras con solapamiento, **dentro de una página** (nunca cruza páginas:
la página es la unidad de cita). Ignora a propósito los límites de sección: es la línea base
contra la que se compara el chunking estructural de la fase 3 (ver docs/ingestion/chunking.md).

Se mide en palabras (no tokens) para no depender de un tokenizador concreto:
en inglés, ~1.3 tokens por palabra -> 225 palabras ≈ 300 tokens.
"""

from __future__ import annotations

from dataclasses import dataclass

from gamerag.ingest.sections import Section

DEFAULT_SIZE = 225
DEFAULT_OVERLAP = 30


@dataclass(frozen=True)
class Window:
    text: str
    first_section: int  # índice (en la lista) de la sección donde empieza
    section_indices: tuple[int, ...]
    n_words: int


def fixed_windows(sections: list[Section], size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Window]:
    if not 0 <= overlap < size:
        raise ValueError("se requiere 0 <= overlap < size")

    # Texto de la página como secuencia de tokens (palabras y saltos de línea), recordando a qué
    # sección pertenece cada uno. Los saltos se conservan para que filas de tablas y listas sigan
    # siendo legibles; solo las palabras cuentan para el tamaño.
    # El título de la sección se antepone como "[A > B]" para dar contexto (y términos para BM25).
    tokens: list[str] = []
    owner: list[int] = []
    for i, sec in enumerate(sections):
        for line in [f"[{sec.title}]", *sec.text.split("\n")]:
            tokens += line.split() + ["\n"]
            owner += [i] * (len(line.split()) + 1)
    word_pos = [k for k, t in enumerate(tokens) if t != "\n"]

    windows: list[Window] = []
    step = size - overlap
    start = 0
    while start < len(word_pos):
        end = min(start + size, len(word_pos))
        lo, hi = word_pos[start], word_pos[end - 1] + 1
        windows.append(Window(
            text=_join(tokens[lo:hi]),
            first_section=owner[lo],
            section_indices=tuple(dict.fromkeys(owner[lo:hi])),
            n_words=end - start,
        ))
        if end == len(word_pos):
            break
        start += step
    return windows


def _join(tokens: list[str]) -> str:
    lines, cur = [], []
    for t in tokens:
        if t == "\n":
            if cur:
                lines.append(" ".join(cur))
            cur = []
        else:
            cur.append(t)
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)
