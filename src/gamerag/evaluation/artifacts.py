"""Contratos reproducibles de evaluación, sin secretos ni dependencias de un índice posterior."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from gamerag.ingest.models import Chunk
from gamerag.retrieval.bm25 import load_chunks

SCHEMA_VERSION = 2
# Una allowlist explícita evita que una nueva credencial de Settings termine en un artefacto.
SAFE_SETTINGS = (
    "profile", "retriever", "generator", "chunker", "embedding_model", "query_expansion", "router",
    "top_k", "candidates", "use_graph", "planner", "evidence_eval", "evidence_mode", "max_rewrites",
    "secondary_search", "secondary_mode", "secondary_k", "secondary_franchise", "memory_notes",
    "only_games", "security_guards", "spoiler_gates", "tool_timeout_s", "llm_model", "llm_cache",
    "llm_offline", "llm_max_tokens", "llm_price_input", "llm_price_output", "llm_run_budget_usd",
)


class EvidenceChunk(Chunk):
    source_hash: str
    is_excerpt: bool = False


def text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_fingerprint(chunks: dict[str, Chunk]) -> str:
    # Incluye revisión, ubicación y permisos, además del texto. Orden independiente de la ingesta.
    payload = [chunks[key].model_dump(mode="json") for key in sorted(chunks)]
    return text_hash(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


def effective_settings(settings) -> dict:
    values = settings.model_dump(mode="json")
    return {key: values[key] for key in SAFE_SETTINGS if key in values}


def run_metadata(settings, *, label: str, dataset: Path | None = None, chunks: dict | None = None) -> dict:
    now = datetime.now(UTC)
    configuration = effective_settings(settings)
    implementation_files = sorted([*(settings.root / "src" / "gamerag").rglob("*.py"),
                                   *(settings.root / "config" / "games").glob("*.yaml")])
    implementation = {str(path.relative_to(settings.root)).replace("\\", "/"): file_hash(path)
                      for path in implementation_files}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=settings.root, capture_output=True,
                                check=True, text=True, timeout=5).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=settings.root,
                                   capture_output=True, check=True, text=True, timeout=5).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, None
    return {
        "schema_version": SCHEMA_VERSION, "run_id": f"{now:%Y%m%dT%H%M%S%fZ}-{uuid4().hex[:8]}",
        "date": now.isoformat(timespec="microseconds"), "label": label,
        "git_commit": commit, "git_dirty": dirty,
        "dataset_sha256": file_hash(dataset) if dataset else None,
        "corpus_sha256": corpus_fingerprint(chunks) if chunks is not None else None,
        "effective_settings": configuration,
        "configuration_sha256": text_hash(json.dumps(configuration, sort_keys=True, separators=(",", ":"))),
        "implementation_sha256": text_hash(json.dumps(implementation, sort_keys=True, separators=(",", ":"))),
        "evidence_format": "authorized_final_context", "human_review": False,
    }


def write_report(out_dir: Path, kind: str, report: dict) -> Path:
    """Nombre único y creación exclusiva: una repetición nunca sustituye resultados anteriores."""
    run = report["run"]
    label = re.sub(r"[^a-zA-Z0-9_-]+", "-", run.get("label", kind)).strip("-") or kind
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run['run_id']}_{kind}_{label}.json"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def historical_chunks(settings, games: set[str]) -> dict[str, Chunk]:
    """Compatibilidad histórica: principal, fuentes secundarias y notas, sin omitir IDs desconocidos."""
    chunks = {}
    for game in sorted(games):
        base = settings.path(settings.data_dir) / "processed" / game
        for path in (base / f"chunks.{settings.chunker}.jsonl", base / f"chunks.{settings.chunker}-multi.jsonl",
                     settings.path(settings.memory_dir) / game / "notes.jsonl"):
            if path.exists():
                chunks.update({c.chunk_id: c for c in load_chunks(path)})
    return chunks


def evidence_chunks(row: dict, chunks: dict[str, Chunk], *, cited: bool = False) -> list[Chunk]:
    """Usa el texto exacto autorizado; nunca sustituye un extracto por el documento íntegro."""
    ids = row.get("sources" if cited else "context", [])
    if "final_evidence" not in row:  # legado: exige todos los IDs para no inflar métricas al omitirlos
        missing = sorted(set(ids) - chunks.keys())
        if missing:
            raise ValueError(f"{row.get('id')}: faltan chunks históricos: {', '.join(missing)}")
        return [chunks[cid] for cid in ids]
    snapshots = {}
    for doc in row["final_evidence"]:
        digest = text_hash(doc["text"])
        if doc.get("evidence_hash") not in (digest, digest.removeprefix("sha256:")):
            raise ValueError(f"{row.get('id')}: evidence_hash inválido: {doc['chunk_id']}")
        cid = doc["chunk_id"]
        if cid in snapshots:
            raise ValueError(f"{row.get('id')}: evidencia duplicada: {cid}")
        metadata = chunks[cid].model_dump() if cid in chunks else {}
        metadata.update(
            chunk_id=cid, text=doc["text"], source=doc["source"], page=doc["page"], version=doc["version"],
            url=doc.get("url", ""), section=doc.get("section", ""), sections=[doc.get("section", "")],
            hash=digest, source_hash=doc.get("source_hash", digest), is_excerpt=doc.get("is_excerpt", False),
            chunker="evidence-snapshot", n_words=len(doc["text"].split()),
            game=row.get("game", ""), kind=chunks[cid].kind if cid in chunks else "source",
        )
        snapshots[cid] = EvidenceChunk(**metadata)
    missing = sorted(set(ids) - snapshots.keys())
    if missing:
        raise ValueError(f"{row.get('id')}: IDs sin evidencia final autorizada: {', '.join(missing)}")
    if not cited and snapshots.keys() != set(ids):
        raise ValueError(f"{row.get('id')}: la evidencia final y los IDs de contexto no coinciden")
    # Cuando el contrato incluye la cita completa, comprobamos la terna, no solo el ID.
    if cited:
        for source in row.get("citations", []):
            doc = snapshots.get(source["chunk_id"])
            if doc is None or (doc.source, doc.page) != (source["source"], source["page"]):
                raise ValueError(f"{row.get('id')}: cita ajena a la evidencia final: {source['chunk_id']}")
    return [snapshots[cid] for cid in ids]


def validate_case_rows(rows: list[dict], cases: dict, *, complete: bool = False) -> None:
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("IDs duplicados en la corrida")
    if set(ids) - cases.keys():
        raise ValueError(f"Casos ajenos al banco: {sorted(set(ids) - cases.keys())}")
    if complete and set(ids) != cases.keys():
        raise ValueError("La corrida no cubre exactamente el banco declarado")
    for row in rows:
        case = cases[row["id"]]
        for key in ("question", "game", "answerable"):
            if key in row and row[key] != getattr(case, key):
                raise ValueError(f"{case.id}: {key} difiere del banco declarado")


def usage_from_calls(calls: list[dict]) -> dict:
    """Uso de esta solicitud; el ledger global nunca se resta entre consultas concurrentes."""
    return {
        "input_tokens": sum(int(c.get("input_tokens") or 0) for c in calls),
        "output_tokens": sum(int(c.get("output_tokens") or 0) for c in calls),
        "cost_usd": round(sum(float(c.get("cost_usd") or 0) for c in calls), 6),
        "llm_call_count": len(calls),
        "http_call_count": sum(int(c.get("attempt") or 0) > 0 for c in calls),
        "llm_cached_calls": sum(bool(c.get("cached")) or c.get("status") == "cache_hit" for c in calls),
        "llm_error_count": sum(c.get("status") == "error" for c in calls),
        "usage_unknown_calls": sum(c.get("usage_known") is False for c in calls),
        "http_retry_count": sum(int(c.get("attempt") or 0) > 1 for c in calls),
    }
