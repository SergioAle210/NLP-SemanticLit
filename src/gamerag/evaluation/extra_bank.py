"""Banco de preguntas que solo responden las wikis extra (para medir la segunda búsqueda).

    uv run python -m gamerag.evaluation.extra_bank --per-game 12        # escribe eval/cases_extra.jsonl

Por cada juego toma chunks al azar de las wikis extra (`origin != strategywiki`) y le pide a Haiku una pregunta, la
respuesta y una **cita literal** del pasaje que la contiene, más 2–4 términos clave. Se conserva el caso solo si:
1. la cita aparece textualmente en el chunk (la evidencia es verificable, como en los demás bancos);
2. StrategyWiki **no** la responde: menos del 60 % de los términos clave aparecen en los 10 mejores chunks de la
   fuente principal para esa pregunta (filtro léxico; es una aproximación, no una garantía).
Los casos usan el esquema de `EvalCase`, así que los evalúan los mismos scripts (`e2e`, `compare`).
"""

from __future__ import annotations

import argparse
import json
import random
import re

from gamerag.games import load_all_games
from gamerag.ingest.models import Chunk
from gamerag.llm import LLMClient
from gamerag.retrieval.bm25 import BM25Index, load_chunks
from gamerag.settings import get_settings

SYSTEM = (
    "You write evaluation questions for a video-game assistant. Given ONE passage, write a question a player "
    "might ask whose answer is stated explicitly in the passage, with a one-sentence answer. Also give a short "
    "VERBATIM quote (at most 18 words, copied exactly) from the passage that contains the answer, and 2-4 key "
    "terms (specific names, numbers or words) the answer depends on. Do not mention 'passage' or 'text'."
)
SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}, "answer": {"type": "string"}, "quote": {"type": "string"},
                   "key_terms": {"type": "array", "items": {"type": "string"}}},
    "required": ["question", "answer", "quote", "key_terms"],
    "additionalProperties": False,
}


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _words(t: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", t.lower()))


def build(llm: LLMClient, game: str, primary: list[Chunk], extra: list[Chunk], n: int,
          rng: random.Random) -> tuple[list[dict], dict]:
    index = BM25Index(primary)
    pool = [c for c in extra if c.kind == "source" and 40 <= c.n_words <= 220]
    rng.shuffle(pool)
    cases, drops = [], {"quote_not_verbatim": 0, "answered_by_primary": 0, "llm_error": 0}
    for c in pool:
        if len(cases) >= n:
            break
        try:
            msg = llm.complete([{"role": "user", "content": f"Passage:\n{' '.join(c.text.split())[:1500]}"}],
                               system=SYSTEM, max_tokens=500, run="extra_bank",
                               output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
            d = json.loads(llm.text(msg))
        except Exception:  # noqa: BLE001 - se descarta ese pasaje
            drops["llm_error"] += 1
            continue
        if _norm(d["quote"]) not in _norm(c.text):
            drops["quote_not_verbatim"] += 1
            continue
        top = " ".join(h.chunk.text for h in index.search(d["question"], k=10))
        terms = [t for t in (_words(k) for k in d["key_terms"]) if t]
        covered = sum(t <= _words(top) for t in terms) / max(1, len(terms))
        if covered >= 0.6:
            drops["answered_by_primary"] += 1
            continue
        cases.append({
            "id": f"extra_{game}_{len(cases):02d}", "question": d["question"], "expected_behavior": d["answer"],
            "expected_sources": [c.source], "expected_pages": [c.page], "answerable": True, "risk_level": "low",
            "category": "direct", "game": game, "profile": "completionist", "lang": "en",
            "evidence": [[d["quote"]]], "author": "assistant",
        })
    return cases, drops


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-game", type=int, default=12)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    s = get_settings()
    llm, rows = LLMClient(s), []
    for game in load_all_games(s.path(s.games_config_dir)):
        base = s.path(s.data_dir) / "processed" / game
        multi = base / f"chunks.{s.chunker}-multi.jsonl"
        if not multi.exists():
            continue
        allc = load_chunks(multi)
        primary = [c for c in allc if c.origin == "strategywiki"]
        extra = [c for c in allc if c.origin != "strategywiki"]
        cases, drops = build(llm, game, primary, extra, args.per_game, random.Random(args.seed))
        rows += cases
        print(f"{game:18} {len(cases):3} casos  descartes={drops}")
    out = s.root / "eval" / "cases_extra.jsonl"
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} casos -> {out}  (gasto acumulado ${llm.ledger.spent():.4f})")


if __name__ == "__main__":
    main()
