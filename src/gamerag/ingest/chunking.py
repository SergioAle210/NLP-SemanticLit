"""Estrategias de chunking (ver docs/ingestion/chunking.md). Ambas operan **dentro de una página**
(nunca cruzan páginas: la página es la unidad de cita) y miden en palabras (no tokens) para no
depender de un tokenizador: en inglés, ~1.3 tokens por palabra -> 225 palabras ≈ 300 tokens.

- `fixed_windows` (línea base, fase 2): ventana deslizante de N palabras con solapamiento que ignora
  a propósito los límites de sección.
- `structural_windows` (fase 3): un chunk por sección; las largas se dividen empaquetando líneas
  completas (filas de tabla, ítems de lista, párrafos) y las diminutas se unen a la siguiente.
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


DEFAULT_MIN_WORDS = 15


def _split_lines(lines: list[str], max_words: int) -> list[list[str]]:
    """Empaqueta líneas completas en bloques de hasta `max_words`. Una línea que excede por sí sola
    el máximo se parte en ventanas de palabras (no ocurre en el corpus actual: máx. 185 palabras)."""
    blocks: list[list[str]] = []
    cur: list[str] = []
    n = 0
    for line in lines:
        w = len(line.split())
        if w > max_words:
            if cur:
                blocks.append(cur)
                cur, n = [], 0
            words = line.split()
            blocks += [[" ".join(words[i:i + max_words])] for i in range(0, len(words), max_words)]
            continue
        if cur and n + w > max_words:
            blocks.append(cur)
            cur, n = [], 0
        cur.append(line)
        n += w
    if cur:
        blocks.append(cur)
    return blocks


def structural_windows(sections: list[Section], max_words: int = DEFAULT_SIZE,
                       min_words: int = DEFAULT_MIN_WORDS) -> list[Window]:
    """Un chunk por sección (o parte de sección), con su ruta como encabezado `[A > B]`.

    - Sección larga -> varios chunks de líneas completas, cada uno con el encabezado repetido.
    - Sección de menos de `min_words` palabras -> se une a la siguiente de la página (si el total
      cabe en `max_words`), para no producir chunks sin contexto (p. ej. "Prerequisites: Raft.").
      El umbral es bajo a propósito: unir secciones con temas distintos reintroduce la dilución.
    Sin solapamiento: los cortes caen en límites de línea, así que no parten ideas.
    """
    # 1. Piezas: (índice de sección, líneas), con las secciones largas ya divididas.
    pieces: list[tuple[int, list[str]]] = []
    for i, sec in enumerate(sections):
        lines = [ln for ln in sec.text.split("\n") if ln.strip()]
        for block in _split_lines(lines, max_words):
            pieces.append((i, block))

    # 2. Unir piezas diminutas con la siguiente.
    def size(group: list[tuple[int, list[str]]]) -> int:
        return sum(len(" ".join(lines).split()) for _, lines in group)

    groups: list[list[tuple[int, list[str]]]] = []
    pending: list[tuple[int, list[str]]] = []
    for piece in pieces:
        if pending and size(pending) + size([piece]) > max_words:  # no cabe: la diminuta queda sola
            groups.append(pending)
            pending = []
        pending.append(piece)
        if size(pending) >= min_words:
            groups.append(pending)
            pending = []
    if pending:  # cola diminuta al final de la página: se une al grupo anterior si cabe
        if groups and size(groups[-1] + pending) <= max_words:
            groups[-1] += pending
        else:
            groups.append(pending)

    # 3. Texto de cada chunk: cada pieza con su encabezado de sección.
    windows = []
    for group in groups:
        parts = [f"[{sections[i].title}]\n" + "\n".join(lines) for i, lines in group]
        text = "\n".join(parts)
        idxs = tuple(dict.fromkeys(i for i, _ in group))
        n_words = sum(len(" ".join(lines).split()) for _, lines in group)
        windows.append(Window(text=text, first_section=idxs[0], section_indices=idxs, n_words=n_words))
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
