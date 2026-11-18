"""Maqueta el informe Markdown en PDF reproducible con tablas y diagramas.

Requiere reportlab, pypdf, Pillow y Graphviz (dot en PATH).
Uso: python scripts/render_report.py docs/course/informe-final.md output/pdf/informe-final.pdf
Los PNG de los diagramas son intermediarios en tmp/pdfs/; no alteramos el Markdown.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#183047")
LIGHT = colors.HexColor("#edf2f5")
PAGE = A4
MARGIN = 2.3 * cm
WIDTH = PAGE[0] - 2 * MARGIN


def inline(text: str) -> str:
    """Texto académico sin énfasis ni tipografía de código dentro de los párrafos."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = html.escape(text)

    def link(match):
        label, url = match.groups()
        if url.startswith(("https://", "http://")):
            return f'<link href="{url}">{label}</link>'
        return label

    return re.sub(r"\[([^]]+)\]\(([^)]+)\)", link, text)


@dataclass(frozen=True)
class Cover:
    title: str
    kind: str
    institution: str
    authors: tuple[str, ...]
    course: str
    date: str
    logo: Path


def extract_cover(raw: str, source: Path) -> tuple[Cover | None, str]:
    """Lee la carátula como texto común antes del primer separador Markdown."""
    parts = re.split(r"^---\s*$", raw, maxsplit=1, flags=re.MULTILINE)
    if len(parts) != 2:
        return None, raw
    preamble, body = parts
    logo = re.search(r"!\[[^]]*\]\(([^)]+)\)", preamble)
    if logo is None:
        return None, raw
    fields = [line.strip() for line in preamble.splitlines() if line.strip() and not line.startswith("![")]
    if len(fields) < 6 or not fields[0].startswith("# "):
        raise ValueError("La carátula requiere título, tipo, institución, integrantes, curso y fecha")
    logo_path = (source.parent / logo[1]).resolve()
    if not logo_path.is_file():
        raise FileNotFoundError(f"No se encontró el logotipo de la carátula: {logo_path}")
    cover = Cover(fields[0][2:], fields[1], fields[2], tuple(fields[3:-2]), fields[-2], fields[-1], logo_path)
    return cover, body


def draw_cover(canvas, cover: Cover) -> None:
    """Carátula centrada según el ejemplo académico del equipo, sin encabezado ni folio."""
    canvas.saveState()
    canvas.setFillColor(colors.black)
    center = PAGE[0] / 2
    canvas.setFont("Times-Bold", 12)
    canvas.drawCentredString(center, PAGE[1] - 2.05 * cm, cover.institution.upper())

    logo = ImageReader(str(cover.logo))
    logo_width, logo_height = logo.getSize()
    width = 5.2 * cm
    height = width * logo_height / logo_width
    canvas.drawImage(logo, center - width / 2, PAGE[1] - 4.7 * cm - height,
                     width=width, height=height, preserveAspectRatio=True, mask="auto")

    title_style = ParagraphStyle("CoverTitle", fontName="Times-Bold", fontSize=14,
                                 leading=19, alignment=TA_CENTER)
    title = Paragraph(inline(cover.title), title_style)
    title_width = PAGE[0] - 4.4 * cm
    _, title_height = title.wrap(title_width, 4 * cm)
    title.drawOn(canvas, (PAGE[0] - title_width) / 2, PAGE[1] - 14.2 * cm - title_height)
    canvas.setFont("Times-Roman", 12)
    canvas.drawCentredString(center, PAGE[1] - 16.6 * cm, cover.kind)
    for index, author in enumerate(cover.authors):
        canvas.drawCentredString(center, PAGE[1] - 19.3 * cm - index * 18, author)
    canvas.drawCentredString(center, PAGE[1] - 25.6 * cm, cover.course)
    canvas.setFont("Times-Bold", 12)
    place, separator, date = cover.date.partition(",")
    canvas.drawCentredString(center, PAGE[1] - 28.2 * cm, place.upper() + separator + date)
    canvas.restoreState()


def diagram(code: str, target: Path) -> Image:
    """Subconjunto Mermaid usado por el informe; conserva nodos, condiciones y aristas."""
    nodes = {}
    pattern = re.compile(r'(\w+)\s*(\[\(\s*"([^"]+)"\s*\)\]|\["([^"]+)"\]|\{"([^"]+)"\})')
    for match in pattern.finditer(code):
        label = next(g for g in match.groups()[2:] if g is not None)
        nodes[match[1]] = (label, "diamond" if match[2].startswith("{") else "box")
    edges = []
    edge_pattern = re.compile(r"\b(\w+)\s*(-\.->|-->)\s*(?:\|([^|]*)\|\s*)?(\w+)\b")
    stripped = pattern.sub(lambda m: m[1], code)
    for line in stripped.splitlines()[1:]:
        line = line.strip()
        if not line or line.startswith("%%"):
            continue
        found = list(edge_pattern.finditer(line))
        if not found:
            raise ValueError(f"Sintaxis de diagrama no soportada: {line}")
        for match in found:
            left, arrow, label, right = match.groups()
            if left not in nodes or right not in nodes:
                raise ValueError(f"Nodo sin definición: {left} -> {right}")
            edges.append((left, right, label or "", arrow == "-.->"))
    lines = ['digraph G {', 'graph [rankdir=TB, bgcolor="white", ranksep=0.35, nodesep=0.3, splines=ortho];',
             'node [shape=box, style="rounded,filled", fillcolor="#edf2f5", color="#456276",',
             'fontname="Arial", fontsize=11, margin="0.09,0.06"];',
             'edge [fontname="Arial", fontsize=9, color="#456276", arrowsize=0.6];']
    for key, (label, shape) in nodes.items():
        wrapped = "\n".join(textwrap.wrap(label.replace("<br/>", " "), 32))
        lines.append(f'{key} [label={json.dumps(wrapped, ensure_ascii=False)}, shape={shape}];')
    for left, right, label, dashed in edges:
        # Un fondo opaco mantiene legibles las condiciones cuando cruzan otras aristas.
        caption = ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2" BGCOLOR="white">'
                   f'<TR><TD>{html.escape(label)}</TD></TR></TABLE>>') if label else '""'
        lines.append(f'{left} -> {right} [xlabel={caption}, '
                     f'style={"dashed" if dashed else "solid"}];')
    lines.append("}")
    target.parent.mkdir(parents=True, exist_ok=True)
    dot = target.with_suffix(".dot")
    dot.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=180", str(dot), "-o", str(target)], check=True)
    image = Image(str(target))
    ratio = min(WIDTH / image.imageWidth, 18.5 * cm / image.imageHeight)
    image.drawWidth, image.drawHeight = image.imageWidth * ratio, image.imageHeight * ratio
    image.hAlign = "CENTER"
    return image


def render(source: Path, output: Path, document_kind: str | None = None) -> dict:
    source_bytes = source.read_bytes()
    raw = source_bytes.decode("utf-8")
    cover, raw = extract_cover(raw, source)
    document_kind = cover.kind if cover else document_kind or "Informe técnico final"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Academic", fontName="Times-Roman", fontSize=11.5, leading=15.5,
                              alignment=TA_JUSTIFY, spaceAfter=7, allowWidows=0, allowOrphans=0))
    styles.add(ParagraphStyle("Cell", fontName="Times-Roman", fontSize=9.5, leading=12, spaceAfter=0))
    styles.add(ParagraphStyle("CodeLine", fontName="Courier", fontSize=8.3, leading=11, spaceAfter=2))
    styles.add(ParagraphStyle("FigureCaption", fontName="Times-Roman", fontSize=10, leading=13,
                              alignment=TA_JUSTIFY, spaceAfter=10))
    styles.add(ParagraphStyle("Reference", fontName="Times-Roman", fontSize=10.5, leading=14,
                              alignment=TA_LEFT, spaceAfter=7, allowWidows=0, allowOrphans=0))
    styles["Title"].fontName = "Times-Bold"
    styles["Title"].fontSize, styles["Title"].leading = 21, 25
    for key in ("Heading1", "Heading2", "Title"):
        styles[key].fontName = "Times-Bold"
        styles[key].textColor = INK
        styles[key].keepWithNext = True
    styles["Heading1"].fontSize, styles["Heading1"].leading = 14, 18
    styles["Heading1"].spaceBefore, styles["Heading1"].spaceAfter = 14, 8
    styles["Heading2"].fontSize, styles["Heading2"].leading = 11.5, 15
    lines = raw.splitlines()
    story, i, figure_count = [], 0, 0
    references = False
    if cover:
        story.extend([Spacer(1, 1), PageBreak()])
    temporary = Path("tmp/pdfs") / source.stem
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("<!--"):
            i += 1
            continue
        if line.startswith("```"):
            lang = line[3:].strip()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            if lang == "mermaid":
                figure_count += 1
                figure = diagram("\n".join(code), temporary / f"flow-{figure_count}.png")
                caption_index = i + 1
                while caption_index < len(lines) and not lines[caption_index].strip():
                    caption_index += 1
                if caption_index < len(lines) and lines[caption_index].startswith("Figura "):
                    caption = Paragraph(inline(lines[caption_index]), styles["FigureCaption"])
                    story.append(KeepTogether([Spacer(1, 6), figure, Spacer(1, 7), caption]))
                    i = caption_index
                else:
                    story.extend([Spacer(1, 6), figure, Spacer(1, 6)])
            else:
                for code_line in code:
                    story.append(Paragraph(html.escape(code_line), styles["CodeLine"]))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells):
                    rows.append(cells)
                i += 1
            columns = len(rows[0])
            if any(len(row) != columns for row in rows):
                raise ValueError("Tabla irregular; escapar separadores literales antes de maquetar")
            widths = [WIDTH / columns] * columns
            if columns == 4 and rows[0][0] == "Medida":
                widths = [WIDTH * share for share in (0.34, 0.22, 0.22, 0.22)]
            elif columns == 5 and rows[0][0] == "Configuración":
                widths = [WIDTH * share for share in (0.30, 0.175, 0.175, 0.175, 0.175)]
            table = Table([[Paragraph(inline(c), styles["Cell"]) for c in row] for row in rows],
                          colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, INK),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#cbd4da")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            table_group = [table]
            if story and isinstance(story[-1], Paragraph) and story[-1].style.name in ("Heading1", "Heading2"):
                table_group.insert(0, story.pop())
            if cover:
                story.extend([KeepTogether(table_group), Spacer(1, 9)])
            else:
                story.extend([*table_group, Spacer(1, 9)])
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading:
            style = {1: "Title", 2: "Heading1", 3: "Heading2"}[len(heading[1])]
            references = "Referencias" in heading[2]
            if heading[2] == "Referencias bibliográficas":
                story.append(PageBreak())
            story.append(Paragraph(inline(heading[2]), styles[style]))
            i += 1
            continue
        if line == "Enlace al video de presentación en YouTube:":
            story.append(KeepTogether([
                Paragraph(inline(line), styles["Academic"]), Spacer(1, 16),
                HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#8b8b8b")),
                Spacer(1, 16),
            ]))
            i += 1
            continue
        bullet = re.match(r"^(?:[-*]|\d+\.)\s+(.*)", line)
        if bullet:
            story.append(Paragraph(inline(line), styles["Reference" if references else "Academic"]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```|[-*] |\d+\. )", lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(" ".join(paragraph)), styles["Reference" if references else "Academic"]))

    def furniture(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#b8c5cf"))
        canvas.line(MARGIN, PAGE[1] - 1.6 * cm, PAGE[0] - MARGIN, PAGE[1] - 1.6 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK)
        canvas.drawString(MARGIN, PAGE[1] - 1.35 * cm, "GameRAG")
        canvas.drawRightString(PAGE[0] - MARGIN, PAGE[1] - 1.35 * cm,
                               document_kind)
        canvas.drawRightString(PAGE[0] - MARGIN, 1.35 * cm, str(doc.page - int(cover is not None)))
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=2.15 * cm, bottomMargin=2.0 * cm,
                            title=cover.title if cover else f"GameRAG - {document_kind}",
                            author="; ".join(cover.authors) if cover else "Equipo GameRAG")
    first_page = (lambda canvas, doc: draw_cover(canvas, cover)) if cover else furniture
    doc.build(story, onFirstPage=first_page, onLaterPages=furniture)
    pages = len(PdfReader(output).pages)
    manifest = {"source": source.as_posix(), "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "pdf": output.as_posix(), "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "pages": pages, "figures": figure_count, "page_format": "A4", "font_size_pt": 11.5,
                "leading_pt": 15.5, "meets_page_range": 10 <= pages <= 15}
    if cover:
        manifest.update({"cover_pages": 1, "content_pages": pages - 1,
                         "logo_sha256": hashlib.sha256(cover.logo.read_bytes()).hexdigest()})
    else:
        manifest.update({"cover_pages": 0, "content_pages": pages})
    output.with_suffix(".layout.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                 encoding="utf-8", newline="\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--document-kind", help="Tipo de documento para encabezados cuando no hay carátula")
    args = parser.parse_args()
    print(json.dumps(render(args.source, args.output, args.document_kind), indent=2))
