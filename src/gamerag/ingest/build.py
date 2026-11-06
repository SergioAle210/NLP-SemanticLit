"""Construye los chunks de un juego a partir de su snapshot de la wiki.

Uso:
    uv run python -m gamerag.ingest.build zelda1                          # fijo (línea base)
    uv run python -m gamerag.ingest.build zelda1 --chunker structural     # estructural (fase 3)
    uv run python -m gamerag.ingest.build ninja_gaiden_nes --size 225 --overlap 30

Salida (regenerable, fuera de git):
    data/processed/<game>/chunks.<chunker>.jsonl   un Chunk por línea
    data/processed/<game>/stats.<chunker>.json     estadísticas para revisar la ingesta
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Literal

from gamerag.games import GameConfig, load_all_games
from gamerag.ingest.chunking import (
    DEFAULT_MIN_WORDS,
    DEFAULT_OVERLAP,
    DEFAULT_SIZE,
    fixed_windows,
    structural_windows,
)
from gamerag.ingest.clean import CleanStats, clean_wikitext
from gamerag.ingest.location import locate
from gamerag.ingest.models import Chunk
from gamerag.ingest.sections import split_sections
from gamerag.settings import get_settings

ChunkerName = Literal["fixed", "structural", "rows"]


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def build_chunks(cfg: GameConfig, root: Path, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP,
                 chunker: ChunkerName = "fixed", min_words: int = DEFAULT_MIN_WORDS):
    snap = root / cfg.snapshot_dir
    manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    stats = CleanStats()
    if chunker == "fixed":
        chunker_id = f"fixed-w{size}-o{overlap}"
        make_windows = lambda secs: fixed_windows(secs, size, overlap)  # noqa: E731
    elif chunker == "structural":
        chunker_id = f"structural-w{size}-m{min_words}"
        make_windows = lambda secs: structural_windows(secs, size, min_words)  # noqa: E731
    elif chunker == "rows":  # estructural + una fila de tabla / celda de mapa por chunk
        chunker_id = f"rows-w{size}-m{min_words}"
        make_windows = lambda secs: structural_windows(secs, size, min_words, split_rows=True)  # noqa: E731
    else:
        raise ValueError(f"chunker desconocido: {chunker}")
    chunks: list[Chunk] = []
    pages_used = 0

    for page in manifest["pages"]:
        if page["title"] in cfg.exclude_pages:
            continue
        text = clean_wikitext((snap / page["file"]).read_text(encoding="utf-8"), stats)
        sections = split_sections(text)
        if not sections:
            continue
        pages_used += 1
        page_slug = _slug(page["title"].removeprefix(cfg.title).removeprefix(" (NES)")) or "main"
        for n, w in enumerate(make_windows(sections)):
            first = sections[w.first_section]
            chunks.append(Chunk(
                chunk_id=f"{cfg.game_id}:{page_slug}:{n:03d}",
                text=w.text,
                source=page["title"],
                page=first.index,
                version=f"revid:{page['revid']}",
                url=page["url"],
                section=first.title,
                sections=[sections[i].title for i in w.section_indices],
                hash="sha256:" + hashlib.sha256(w.text.encode("utf-8")).hexdigest(),
                chunker=chunker_id,
                n_words=w.n_words,
                game=cfg.game_id,
                location=locate(cfg, page["title"], first),
            ))

    lengths = [c.n_words for c in chunks]
    report = {
        "game": cfg.game_id,
        "chunker": chunker_id,
        "pages_in_snapshot": len(manifest["pages"]),
        "pages_used": pages_used,
        "chunks": len(chunks),
        "words": {"min": min(lengths), "mean": round(statistics.mean(lengths), 1), "max": max(lengths)},
        "chunks_spanning_multiple_sections": sum(len(c.sections) > 1 for c in chunks),
        "chunks_with_location": sum(c.location != c.location.__class__() for c in chunks),
        "unknown_templates": dict(stats.unknown_templates),
    }
    return chunks, report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("game_id")
    ap.add_argument("--chunker", choices=["fixed", "structural", "rows"], default="fixed")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="palabras máximas por chunk")
    ap.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="solapamiento (solo fixed)")
    ap.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS, help="unir secciones menores (solo structural)")
    args = ap.parse_args()

    settings = get_settings()
    games = load_all_games(settings.path(settings.games_config_dir))
    if args.game_id not in games:
        ap.error(f"juego desconocido: {args.game_id}. Opciones: {', '.join(games)}")

    chunks, report = build_chunks(games[args.game_id], settings.root, args.size, args.overlap,
                                  args.chunker, args.min_words)

    out = settings.path(settings.data_dir) / "processed" / args.game_id
    out.mkdir(parents=True, exist_ok=True)
    with (out / f"chunks.{args.chunker}.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(c.model_dump_json() + "\n")
    (out / f"stats.{args.chunker}.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=2))
    print(f"-> {out / f'chunks.{args.chunker}.jsonl'}")


if __name__ == "__main__":
    main()
