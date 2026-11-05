"""Limpieza de wikitext de StrategyWiki a texto plano legible.

Diseño (ver docs/ingestion/cleaning.md):
1. Plantillas ({{...}}) -> reglas explícitas por nombre (se procesan de adentro hacia afuera).
2. Enlaces: imágenes/categorías se eliminan; el resto se reemplaza por su texto visible.
3. Etiquetas HTML: galerías/imagemaps se eliminan; las demás conservan su contenido.
4. Tablas wiki ({| ... |}) -> una línea por fila con pares "Encabezado: valor".
5. Marcado residual (negritas, listas, palabras mágicas) -> texto plano.

Las plantillas sin regla se descartan y se cuentan en `CleanStats.unknown_templates`, para que
una plantilla nueva no se pierda en silencio.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import mwparserfromhell
from mwparserfromhell.nodes import Tag, Template, Text, Wikilink

# --- Reglas de plantillas -------------------------------------------------------------------

# Navegación, maquetación y metadatos del sitio: no aportan contenido del juego.
DROP = {
    "header nav", "footer nav", "floatingtoc", "-", "col", "toc", "contentboxcontainer",
    "zeldawiki", "img", "scrolling_map", "scrolling map", "game disambig", "desc",
    "prettytable", "the legend of zelda", "ninja gaiden", "clear",
    "cero", "esrb", "pegi", "oflc",  # clasificaciones por edad (dentro de la ficha {{Game}})
}
# Botones de otras consolas (ports). El alcance es NES: se descartan para no ensuciar la tabla de controles.
NON_NES_BUTTONS = {"gc", "wii", "wii-cc", "3ds", "switch", "wiiu", "gba"}
LITERALS = {"plus": "+", "(": "(", ")": ")"}
# Ficha del juego ({{Game}}): campos con información útil, en el orden en que se escriben.
GAME_INFOBOX_FIELDS = {
    "title": "Title", "japanese": "Japanese title", "developer": "Developer", "publisher": "Publisher",
    "designer": "Designer", "year": "Year", "systems": "Systems", "genre": "Genre", "modes": "Modes",
    "series": "Series", "preceded by": "Preceded by", "followed by": "Followed by",
}


@dataclass
class CleanStats:
    templates: Counter = field(default_factory=Counter)
    unknown_templates: Counter = field(default_factory=Counter)


def _arg(t: Template, key: str | int, default: str = "") -> str:
    key = str(key)
    return str(t.get(key).value).strip() if t.has(key) else default


def _positional(t: Template) -> list[str]:
    return [str(p.value).strip() for p in t.params if not p.showkey]


def _render_template(t: Template, stats: CleanStats) -> str:
    """Devuelve el reemplazo de una plantilla cuyos argumentos ya fueron renderizados."""
    name = str(t.name).strip().lower()
    stats.templates[name] += 1
    pos = _positional(t)

    if name in DROP or name.startswith("defaultsort") or name in NON_NES_BUTTONS:
        return ""
    if name in LITERALS:
        return LITERALS[name]
    if name == "im/loz":  # {{im/loz|Item|Raft}} -> Raft
        return pos[1] if len(pos) > 1 else (pos[0] if pos else "")
    if name in {"a", "c", "n/a"}:  # enlace a artículo / juego / no aplica
        return pos[0] if pos else ""
    if name == "nes":  # {{nes|A}} -> A ; {{nes|Up|Dpad}} -> Up (D-pad) ; {{nes|Neutral|Dpad}} -> D-pad
        if len(pos) > 1 and pos[1].lower() == "dpad":
            return "D-pad" if pos[0].lower() == "neutral" else f"{pos[0]} (D-pad)"
        return pos[0] if pos else ""
    if name in {"h2", "h3"}:  # encabezados dentro de listas de navegación
        return f"\n{pos[0]}\n" if pos else ""
    if name == "nihongo":  # {{nihongo|Ninja Gaiden|NINJA外伝|}} -> Ninja Gaiden (NINJA外伝)
        extra = [p for p in pos[1:3] if p]
        return f"{pos[0]} ({', '.join(extra)})" if extra else (pos[0] if pos else "")
    if name in {"colist", "syslist"}:
        return ", ".join(p for p in pos if p)
    if name == "contentbox":  # fichas de objetos en secuencia -> subsección propia
        return f"\n=== {_arg(t, 'title')} ===\n{_arg(t, 'contents')}\n"
    if name == "game":  # ficha del juego -> una línea "Campo: valor" por dato útil
        lines = [
            f"{label}: {', '.join(p.strip() for p in v.splitlines() if p.strip())}"  # <br> -> coma
            for key, label in GAME_INFOBOX_FIELDS.items() if (v := _arg(t, key))
        ]
        return "\n" + "\n".join(lines) + "\n" if lines else ""
    if name == "sidebar":  # nota al margen -> párrafo (como encabezado "robaría" el texto siguiente)
        return f"\n{_arg(t, 'title')}: {_arg(t, 'contents')}\n"

    stats.unknown_templates[name] += 1
    return ""


def _render_node(node, stats: CleanStats) -> str:
    if isinstance(node, Template):
        for param in node.params:  # adentro hacia afuera: primero los argumentos
            param.value = _render_wikicode(param.value, stats)
        return _render_template(node, stats)
    if isinstance(node, Wikilink):
        target = str(node.title).strip()
        if re.match(r"(?i)^(file|image|category)\s*:", target):
            return ""
        if node.text is not None:
            return _render_wikicode(node.text, stats)
        return target.rstrip("/").split("/")[-1]  # [[A/B/C]] -> C
    if isinstance(node, Tag):
        tag = str(node.tag).lower()
        if tag in {"gallery", "imagemap", "ref"}:
            return ""
        if tag == "br":
            return "\n"
        if node.wiki_markup:  # '''negrita''', ''cursiva'', listas, tablas: conservar el marcado
            raw = str(node)
            if node.contents is None or not str(node.contents):
                return raw
            return raw.replace(str(node.contents), _render_wikicode(node.contents, stats), 1)
        return _render_wikicode(node.contents, stats) if node.contents is not None else ""
    if isinstance(node, Text):
        return str(node)
    return str(node)  # comentarios, entidades HTML, etc.


def _render_wikicode(code, stats: CleanStats) -> str:
    if not hasattr(code, "nodes"):
        code = mwparserfromhell.parse(str(code))
    return "".join(_render_node(n, stats) for n in code.nodes)


# --- Tablas ---------------------------------------------------------------------------------

_ATTR = re.compile(r'^\s*[a-z-]+\s*=\s*("[^"]*"|\S+)(\s+[a-z-]+\s*=\s*("[^"]*"|\S+))*\s*\|(?!\|)', re.I)


@dataclass
class _Cell:
    header: bool  # celda "!" (encabezado o etiqueta de fila)
    text: str
    colspan: int = 1
    rowspan: int = 1


def _cell(raw: str, header: bool) -> _Cell:
    """Separa atributos (`width="10%" colspan="3"| valor`) del contenido."""
    m = _ATTR.match(raw)
    attrs = m.group(0) if m else ""
    span = {k: int(v) for k, v in re.findall(r'(colspan|rowspan)\s*=\s*"?(\d+)', attrs, re.I)}
    return _Cell(header, raw[len(attrs):].strip(), span.get("colspan", 1), span.get("rowspan", 1))


def _parse_rows(lines: list[str]) -> list[list[_Cell]]:
    rows: list[list[_Cell]] = []
    current: list[_Cell] = []
    for line in lines[1:]:  # lines[0] es '{|'
        s = line.strip()
        if s.startswith("|}"):
            break
        if s.startswith("|+"):
            continue  # caption
        if s.startswith("|-"):
            if current:
                rows.append(current)
            current = []
        elif s.startswith("!"):
            current += [_cell(c, True) for c in re.split(r"!!|\|\|", s[1:])]
        elif s.startswith("|"):
            current += [_cell(c, False) for c in s[1:].split("||")]
        elif current:  # continuación multilínea de la última celda
            current[-1].text = f"{current[-1].text}\n{s}".strip()
    if current:
        rows.append(current)
    return rows


def _expand_spans(rows: list[list[_Cell]]) -> list[list[_Cell]]:
    """Alinea las celdas a su columna real: colspan deja huecos a la derecha y rowspan en filas siguientes."""
    carry: dict[int, int] = {}  # columna -> filas que aún ocupa una celda con rowspan
    out = []
    for row in rows:
        grid: list[_Cell] = []
        cells = iter(row)
        col = 0
        while True:
            if carry.get(col, 0) > 0:
                carry[col] -= 1
                grid.append(_Cell(False, ""))
                col += 1
                continue
            cell = next(cells, None)
            if cell is None:
                break
            for k in range(cell.colspan):
                grid.append(cell if k == 0 else _Cell(cell.header, ""))
                if cell.rowspan > 1:
                    carry[col + k] = cell.rowspan - 1
            col += cell.colspan
        out.append(grid)
    return out


def _norm(v: str) -> str:
    # Listas dentro de una celda ("*a\n*b") -> "a; b"
    items = [re.sub(r"^[*#]+\s*", "", ln).strip() for ln in v.split("\n")]
    return "; ".join(i for i in items if i)


def _meaningful(v: str) -> bool:
    # Descarta restos de columnas vaciadas (p. ej. botones de otras consolas: "/", "+*", "—")
    return bool(re.search(r"\w", v))


def _flatten_table(lines: list[str]) -> list[str]:
    """Convierte una tabla wiki en líneas de texto autocontenidas.

    - Tabla con encabezados: una línea por fila, "Encabezado: valor | ...".
    - Cuadrícula de mapa (esquina vacía + etiqueta de fila): una línea por celda con su
      coordenada "Columna-Fila: valor" (p. ej. "B-2: ..."), como se citan en el resto de la wiki.
    - Sin encabezados: los valores de la fila.
    """
    rows = _expand_spans(_parse_rows(lines))
    for row in rows:
        for c in row:
            c.text = _norm(c.text)

    headers: list[str] = []
    if rows and all(c.header for c in rows[0]) and any(c.text for c in rows[0]):
        headers = [c.text for c in rows.pop(0)]
    is_grid = len(headers) > 1 and headers[0] == "" and all(headers[1:])

    out = []
    for row in rows:
        values = [c.text for c in row]
        if is_grid and row and row[0].header and row[0].text:
            label = row[0].text
            out += [f"{h}-{label}: {v}" for h, v in zip(headers[1:], values[1:], strict=False) if _meaningful(v)]
            continue
        if headers and len(values) == len(headers):
            pairs = [f"{h}: {v}" for h, v in zip(headers, values, strict=True) if h and _meaningful(v)]
        else:
            pairs = [v for v in values if _meaningful(v)]
        if pairs:
            out.append(" | ".join(pairs))
    return out


def _flatten_tables(text: str) -> str:
    out, buf, depth = [], [], 0
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("{|"):
            depth += 1
        if depth:
            buf.append(line)
            if s.startswith("|}"):
                depth -= 1
                if depth == 0:
                    out.extend(_flatten_table(buf))
                    buf = []
            continue
        out.append(line)
    out.extend(buf)  # tabla sin cerrar: se deja tal cual
    return "\n".join(out)


# --- Marcado residual -----------------------------------------------------------------------

def _strip_markup(text: str) -> str:
    text = re.sub(r"__[A-Z]+__", "", text)  # __TOC__, __NOTOC__
    text = re.sub(r"'{2,}", "", text)  # negritas/cursivas
    text = re.sub(r"^[*#]+\s*", "- ", text, flags=re.M)  # listas
    text = re.sub(r"^;\s*", "", text, flags=re.M)  # términos de definición
    text = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", text)  # enlaces externos con texto
    text = re.sub(r"<[^>]+>", "", text)  # etiquetas HTML residuales
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_wikitext(wikitext: str, stats: CleanStats | None = None) -> str:
    """Wikitext -> texto plano. Conserva los encabezados `== X ==` para la segmentación."""
    stats = stats if stats is not None else CleanStats()
    rendered = _render_wikicode(mwparserfromhell.parse(wikitext), stats)
    return _strip_markup(_flatten_tables(rendered))
