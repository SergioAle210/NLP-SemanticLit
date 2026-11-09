"""Dreaming: consolidación offline de las trazas en notas de memoria verificadas.

    uv run python -m gamerag.dream --traces state/traces_train.sqlite3 --game zelda1

Lee las trazas guardadas (tabla `audit`), elige las que enseñan algo reutilizable y escribe notas en
`data/memory/<juego>/notes.jsonl` (formato `Chunk`, `kind="note"`):

- **multi-salto**: una respuesta que combinó 2+ chunks tras descomponer la pregunta -> una nota que junta esos
  datos (así la próxima vez basta una búsqueda);
- **reescritura**: una abstención recuperada por el evaluador de evidencia -> una nota con la formulación que
  funcionó como alias de recuperación.

Garantías (ver docs/memoria-y-tecnicas-avanzadas.md):
1. Una nota se redacta **solo** con el texto de sus fuentes (las citadas en la traza).
2. Se **verifica** de forma determinista: toda cifra y todo nombre propio de la nota debe aparecer en las
   fuentes, y cada oración debe solaparse con ellas; si no, se descarta y se registra el motivo.
3. Guarda `derived_from`; el acceso lo resuelve `ProvenanceFilter` (la nota solo se muestra a quien puede ver
   todas sus fuentes), no una etiqueta copiada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from gamerag.ingest.models import Chunk
from gamerag.llm import BudgetExceeded, LLMClient
from gamerag.retrieval.bm25 import load_chunks
from gamerag.settings import Settings, get_settings
from gamerag.store import Store

SYSTEM = (
    "You write a short reference note for a NES game wiki search index. Use ONLY facts stated in the provided "
    "source passages: do not add, infer or generalize anything. Name every entity explicitly (items, bosses, "
    "locations) and keep numbers exactly as written. Do not mention anything absent from the passages "
    "(not even the platform or game name). The note must be at most 90 words. Also give 2-3 short "
    "player-style questions this note answers."
)
SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "text": {"type": "string"},
                   "questions": {"type": "array", "items": {"type": "string"}}},
    "required": ["title", "text", "questions"],
    "additionalProperties": False,
}

_WORD = re.compile(r"[A-Za-z0-9']+")
_STOP = {"the", "and", "that", "with", "this", "from", "have", "will", "which", "their", "your", "link", "also",
         "when", "into", "than", "only", "each", "does", "must", "once", "they", "them", "then", "there"}


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text)}


def verify_note(note: str, sources: list[str]) -> str | None:
    """None si la nota está respaldada por las fuentes; si no, el motivo del rechazo."""
    src_text = " ".join(sources)
    src = _tokens(src_text)
    missing_nums = {n for n in re.findall(r"\d+", note) if n not in set(re.findall(r"\d+", src_text))}
    if missing_nums:
        return f"numbers_not_in_sources:{sorted(missing_nums)}"
    for sentence in re.split(r"(?<=[.!?])\s+", note.strip()):
        words = _WORD.findall(sentence)
        proper = {w.lower() for w in words[1:] if w[:1].isupper()}
        if proper - src:
            return f"entities_not_in_sources:{sorted(proper - src)}"
        content = {w.lower() for w in words if len(w) > 3 and w.lower() not in _STOP}
        if content and len(content & src) / len(content) < 0.6:
            return f"low_overlap:{sentence[:60]!r}"
    return None


def candidates(traces: list[dict]) -> list[tuple[str, dict]]:
    """(motivo, traza) de las trazas útiles; una por conjunto de fuentes citadas."""
    seen: set[frozenset[str]] = set()
    out: list[tuple[str, dict]] = []
    for t in traces:
        if t.get("outcome") != "answered" or not t.get("cited"):
            continue
        key = frozenset(t["cited"])
        if key in seen:
            continue
        if len(t.get("subqueries", [])) > 1 and len(key) >= 2:
            reason = "multihop"
        elif any(not e.get("sufficient", True) and e.get("rewrite") for e in t.get("evidence", [])):
            reason = "rewrite"
        else:
            continue
        seen.add(key)
        out.append((reason, t))
    return out


def make_note(llm: LLMClient, sources: list[Chunk], run: str = "dream") -> dict:
    docs = "\n\n".join(f"[{c.chunk_id}] {' '.join(c.text.split())}" for c in sources)
    msg = llm.complete([{"role": "user", "content": f"Source passages:\n{docs}"}], system=SYSTEM, max_tokens=700,
                       run=run, output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
    return json.loads(llm.text(msg))


def note_chunk(game: str, sources: list[Chunk], data: dict, reason: str) -> Chunk:
    qs = " ".join(f"Q: {q}" for q in data["questions"])
    text = f"{data['title']}. {data['text'].strip()} {qs}".strip()
    digest = hashlib.sha256((",".join(sorted(c.chunk_id for c in sources)) + text).encode()).hexdigest()[:10]
    first = sources[0]
    deepest = max(sources, key=lambda c: (c.location.level or 0, c.location.act or 0))
    return Chunk(chunk_id=f"{game}:note:{digest}", text=text, source=first.source, page=first.page,
                 version=first.version, url=first.url, section=f"note/{reason}", sections=[f"note/{reason}"],
                 hash=hashlib.sha256(text.encode()).hexdigest(), chunker="dream", n_words=len(text.split()),
                 lang=first.lang, game=game, location=deepest.location, kind="note",
                 derived_from=[c.chunk_id for c in sources])


def dream(traces: list[dict], chunks_by_id: dict[str, Chunk], llm: LLMClient, game: str,
          max_notes: int = 20) -> tuple[list[Chunk], list[dict]]:
    notes: list[Chunk] = []
    rejected: list[dict] = []
    for reason, t in candidates(traces):
        if len(notes) >= max_notes:
            break
        sources = [chunks_by_id[c] for c in t["cited"] if c in chunks_by_id and chunks_by_id[c].kind == "source"]
        if not sources:
            continue
        try:
            data = make_note(llm, sources)
        except BudgetExceeded:
            raise
        except Exception as exc:  # noqa: BLE001 - un fallo del LLM descarta ese candidato
            rejected.append({"trace": t["trace_id"], "reason": f"llm_error:{type(exc).__name__}"})
            continue
        problem = verify_note(data["text"], [c.text for c in sources])  # el título es solo una etiqueta
        if problem:
            rejected.append({"trace": t["trace_id"], "reason": problem, "text": data["text"]})
            continue
        notes.append(note_chunk(game, sources, data, reason))
    return notes, rejected


def write_notes(path: Path, notes: list[Chunk]) -> int:
    """Fusiona con las notas existentes por chunk_id (idempotente)."""
    existing = {c.chunk_id: c for c in load_chunks(path)} if path.exists() else {}
    existing.update({c.chunk_id: c for c in notes})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(c.model_dump_json() for c in existing.values()) + "\n", encoding="utf-8",
                    newline="\n")
    return len(existing)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--traces", required=True, help="SQLite con la tabla audit (state/gamerag.sqlite3 u otra)")
    ap.add_argument("--game", required=True)
    ap.add_argument("--max-notes", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true", help="solo lista los candidatos; no llama al LLM")
    args = ap.parse_args()

    s: Settings = get_settings()
    traces = Store(Path(args.traces)).all_traces(args.game)
    cands = candidates(traces)
    print(f"{len(traces)} trazas, {len(cands)} candidatas: "
          f"{sum(r == 'multihop' for r, _ in cands)} multi-salto, {sum(r == 'rewrite' for r, _ in cands)} reescritura")
    if args.dry_run:
        return
    chunks = {c.chunk_id: c for c in load_chunks(
        s.path(s.data_dir) / "processed" / args.game / f"chunks.{s.chunker}.jsonl")}
    notes, rejected = dream(traces, chunks, LLMClient(s), args.game, args.max_notes)
    out = s.path(s.memory_dir) / args.game / "notes.jsonl"
    total = write_notes(out, notes)
    print(f"{len(notes)} notas aceptadas, {len(rejected)} rechazadas -> {out} ({total} en total)")
    for r in rejected:
        print("  rechazada:", r["trace"][:8], r["reason"])


if __name__ == "__main__":
    main()
