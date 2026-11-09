"""Preguntas sintéticas para generar trazas de entrenamiento del dreaming.

    uv run python -m gamerag.evaluation.synth generate --n-single 30 --n-pair 30   # escribe eval/synthetic_train.jsonl
    uv run python -m gamerag.evaluation.synth run --trace-db state/traces_synth.sqlite3

`generate` pide a Haiku una pregunta por chunk (de un solo dato) o por **par de chunks de páginas distintas que
comparten una entidad** (multi-salto). Las preguntas salen solo del corpus, nunca de los bancos de evaluación, así
que las notas que se aprendan de ellas no filtran los casos de prueba. `run` las ejecuta con la configuración
servida (se recomienda planner + evaluador) y guarda las trazas para `gamerag.dream`.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from gamerag.games import load_all_games
from gamerag.ingest.models import Chunk
from gamerag.llm import LLMClient
from gamerag.pipeline import build_pipeline
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import load_chunks
from gamerag.settings import Settings, get_settings
from gamerag.store import Store

SYSTEM = (
    "You write one realistic question a player of a NES game might ask. The question must be answerable using "
    "ONLY the provided passage(s) and, when two passages are given, must need facts from BOTH. Use the player's "
    "vocabulary, name the entities explicitly, never mention 'passage' or 'document', and output one question."
)
SCHEMA = {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"],
          "additionalProperties": False}
_ENTITY = re.compile(r"\b[A-Z][a-z]{3,}(?: [A-Z][a-z]+)?\b")
_COMMON = {"Link", "Level", "Quest", "This", "These", "There", "When", "Name", "Description", "Damage", "Zelda",
           "Ninja", "Gaiden", "Note", "Each", "Many", "Only", "Some", "Then", "After", "Before", "Stage"}


def _entities(c: Chunk) -> set[str]:
    return {e for e in _ENTITY.findall(c.text) if e not in _COMMON}


def pick(chunks: list[Chunk], n_single: int, n_pair: int, rng: random.Random) -> list[tuple[str, list[Chunk]]]:
    sources = [c for c in chunks if c.kind == "source" and c.n_words >= 25]
    singles = [("single", [c]) for c in rng.sample(sources, min(n_single, len(sources)))]
    by_entity: dict[str, list[Chunk]] = defaultdict(list)
    for c in sources:
        for e in _entities(c):
            by_entity[e].append(c)
    pairs, seen = [], set()
    entities = [e for e, cs in by_entity.items() if 2 <= len({c.source for c in cs}) and len(cs) <= 8]
    rng.shuffle(entities)
    for e in entities:
        a, b = rng.sample(by_entity[e], 2)
        key = frozenset((a.chunk_id, b.chunk_id))
        if a.source != b.source and key not in seen:
            seen.add(key)
            pairs.append(("pair", [a, b]))
        if len(pairs) >= n_pair:
            break
    return singles + pairs


def generate(llm: LLMClient, game: str, chunks: list[Chunk], n_single: int, n_pair: int, seed: int) -> list[dict]:
    out = []
    for i, (kind, cs) in enumerate(pick(chunks, n_single, n_pair, random.Random(seed))):
        docs = "\n\n".join(f"[passage {j}] {' '.join(c.text.split())[:700]}" for j, c in enumerate(cs, 1))
        msg = llm.complete([{"role": "user", "content": docs}], system=SYSTEM, max_tokens=120, run="synth",
                           output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
        q = json.loads(llm.text(msg))["question"].strip()
        out.append({"id": f"synth_{game}_{i:03d}", "game": game, "kind": kind, "question": q,
                    "chunk_ids": [c.chunk_id for c in cs]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--n-single", type=int, default=30)
    g.add_argument("--n-pair", type=int, default=30)
    g.add_argument("--seed", type=int, default=7)
    r = sub.add_parser("run")
    r.add_argument("--trace-db", required=True)
    r.add_argument("--file", default="eval/synthetic_train.jsonl")
    args = ap.parse_args()

    s: Settings = get_settings()
    out_path = s.root / "eval" / "synthetic_train.jsonl"
    if args.cmd == "generate":
        llm, rows = LLMClient(s), []
        for game in load_all_games(s.path(s.games_config_dir)):
            path = s.path(s.data_dir) / "processed" / game / f"chunks.{s.chunker}.jsonl"
            if path.exists():
                share = 1 if game == "zelda1" else 0.5  # NG tiene un tercio del corpus
                rows += generate(llm, game, load_chunks(path), int(args.n_single * share), int(args.n_pair * share),
                                 args.seed)
        out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8",
                            newline="\n")
        print(f"{len(rows)} preguntas -> {out_path}  (gasto acumulado ${llm.ledger.spent():.4f})")
        return

    cfg = Settings(root=s.root, spoiler_gates=True)
    pipe = build_pipeline(cfg)
    store = Store(s.path(Path(args.trace_db)))
    unrestricted = Profile(user_id="synth", role="completionist")  # el entrenamiento no filtra por progreso
    rows = [json.loads(line) for line in (s.root / args.file).read_text(encoding="utf-8").splitlines() if line]
    for r in rows:
        if r["game"] in pipe.retrievers:
            _, trace = pipe.ask(r["question"], r["game"], unrestricted)
            store.log_trace(trace)
    print(f"{len(rows)} trazas -> {args.trace_db}  (gasto acumulado ${LLMClient(s).ledger.spent():.4f})")


if __name__ == "__main__":
    main()
