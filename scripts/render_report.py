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
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor("#183047")
LIGHT = colors.HexColor("#edf2f5")
PAGE = A4
MARGIN = 2.3 * cm
WIDTH = PAGE[0] - 2 * MARGIN


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" size="9">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)

    def link(match):
        label, url = match.groups()
        if url.startswith(("https://", "http://")):
            return f'<link href="{url}" color="#265879">{label}</link>'
        return f'<font color="#265879">{label}</font>'

    return re.sub(r"\[([^]]+)\]\(([^)]+)\)", link, text)


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


def render(source: Path, output: Path) -> dict:
    source_bytes = source.read_bytes()
    raw = source_bytes.decode("utf-8")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Academic", fontName="Times-Roman", fontSize=11.5, leading=15.5,
                              alignment=TA_JUSTIFY, spaceAfter=8, allowWidows=0, allowOrphans=0))
    styles.add(ParagraphStyle("Cell", fontName="Times-Roman", fontSize=9.5, leading=12, spaceAfter=0))
    styles.add(ParagraphStyle("CodeLine", fontName="Courier", fontSize=8.3, leading=11, spaceAfter=2))
    styles["Title"].fontName = "Times-Bold"
    styles["Title"].fontSize, styles["Title"].leading = 21, 25
    for key in ("Heading1", "Heading2", "Title"):
        styles[key].textColor = INK
        styles[key].keepWithNext = True
    styles["Heading1"].fontSize, styles["Heading1"].leading = 14, 18
    styles["Heading1"].spaceBefore, styles["Heading1"].spaceAfter = 14, 8
    styles["Heading2"].fontSize, styles["Heading2"].leading = 11.5, 15
    lines = raw.splitlines()
    story, i, figure_count = [], 0, 0
    temporary = Path("tmp/pdfs")
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
                story.extend([Spacer(1, 6), diagram("\n".join(code), temporary / f"flow-{figure_count}.png"),
                              Spacer(1, 6)])
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
            table = Table([[Paragraph(inline(c), styles["Cell"]) for c in row] for row in rows],
                          colWidths=[WIDTH / columns] * columns, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, INK),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#cbd4da")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([KeepTogether([table]), Spacer(1, 9)])
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading:
            style = {1: "Title", 2: "Heading1", 3: "Heading2"}[len(heading[1])]
            story.append(Paragraph(inline(heading[2]), styles[style]))
            i += 1
            continue
        bullet = re.match(r"^(?:[-*]|\d+\.)\s+(.*)", line)
        if bullet:
            story.append(Paragraph(inline(line), styles["Academic"]))
            i += 1
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||```|[-*] |\d+\. )", lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(" ".join(paragraph)), styles["Academic"]))

    def furniture(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#b8c5cf"))
        canvas.line(MARGIN, PAGE[1] - 1.6 * cm, PAGE[0] - MARGIN, PAGE[1] - 1.6 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(INK)
        canvas.drawString(MARGIN, PAGE[1] - 1.35 * cm, "GameRAG | CC3103 | Informe técnico final")
        canvas.drawRightString(PAGE[0] - MARGIN, 1.35 * cm, str(doc.page))
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN,
                            topMargin=2.15 * cm, bottomMargin=2.0 * cm,
                            title="GameRAG - Informe técnico final", author="Equipo GameRAG")
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    pages = len(PdfReader(output).pages)
    manifest = {"source": source.as_posix(), "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "pdf": output.as_posix(), "pdf_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "pages": pages, "figures": figure_count, "page_format": "A4", "font_size_pt": 11.5,
                "leading_pt": 15.5, "meets_page_range": 10 <= pages <= 15}
    output.with_suffix(".layout.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.source, args.output), indent=2))
