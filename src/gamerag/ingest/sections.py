"""Segmentación del texto limpio en secciones según sus encabezados `== X ==`.

Cada sección conserva su ruta jerárquica (p. ej. ["Walkthrough", "Dungeon Walkthrough"]).
Es la base de los metadatos de ubicación y, en la fase 3, del chunking estructural.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")


@dataclass(frozen=True)
class Section:
    index: int  # posición dentro de la página (0 = texto antes del primer encabezado)
    path: tuple[str, ...]  # jerarquía de encabezados
    text: str

    @property
    def title(self) -> str:
        return " > ".join(self.path) if self.path else "(intro)"


def split_sections(clean_text: str) -> list[Section]:
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []  # (nivel, título)
    buf: list[str] = []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            sections.append(Section(len(sections), tuple(t for _, t in stack), body))
        buf.clear()

    for line in clean_text.split("\n"):
        m = _HEADING.match(line.strip())
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            buf.append(line)
    flush()
    return sections
