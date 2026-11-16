"""Dos revisiones reales de un documento sintético, reingestado en la misma ruta.

    python -m gamerag.evaluation.versions
    python -m gamerag.evaluation.versions --dense  # requiere modelo local y extra semantic

No añade un filtro de versión a la API ni mezcla el corpus sintético con los juegos de producción.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from gamerag.evaluation.artifacts import corpus_fingerprint, file_hash, run_metadata, write_report
from gamerag.evaluation.cases import load_cases
from gamerag.evaluation.e2e import _agg, run_case
from gamerag.games import GameConfig
from gamerag.ingest.build import build_chunks
from gamerag.pipeline import Pipeline
from gamerag.progress.models import Profile
from gamerag.retrieval.bm25 import BM25Index, load_chunks
from gamerag.settings import Settings, get_settings

FIXTURE = Path("eval/fixtures/document_versions.json")
BANK = Path("eval/cases_versions.jsonl")


def revision_chunks(root: Path, fixture: dict, revision: dict):
    snapshot = root / "snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    documents = [{"title": fixture["source"], "text": revision["text"]}, *fixture["distractors"]]
    pages = []
    for number, document in enumerate(documents):
        name = f"document-{number}.wiki"
        (snapshot / name).write_text(document["text"], encoding="utf-8", newline="\n")
        pages.append({"title": document["title"], "file": name, "revid": revision["revid"],
                      "url": f"https://example.invalid/synthetic/revision-fixture/{number}"})
    (snapshot / "manifest.json").write_text(json.dumps({"pages": pages}), encoding="utf-8")
    config = GameConfig(game_id="revision_fixture", title="Revision Fixture", platform="synthetic", year=2026,
                        snapshot_dir=Path("snapshot"), progress_model="linear_stage", stages=["training"], tools=[])
    return build_chunks(config, root, chunker="structural", min_words=1)[0]


def run_revisions(settings: Settings, workspace: Path, *, embedder=None) -> dict:
    fixture_path, bank_path = settings.root / FIXTURE, settings.root / BANK
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = {case.id: case for case in load_cases(bank_path)}
    profile = Profile(user_id="fixture", role="player",
                      progress={"revision_fixture": {"kind": "linear_stage", "current_stage": "training"}})
    persisted = workspace / "chunks.structural.jsonl"
    rows, fingerprints = [], []
    for revision in fixture["revisions"]:
        chunks = revision_chunks(workspace, fixture, revision)
        # La ruta es idéntica en ambas ingestas y se vuelve a leer antes de indexar.
        persisted.write_text("\n".join(chunk.model_dump_json() for chunk in chunks) + "\n", encoding="utf-8")
        current = load_chunks(persisted)
        chunk_index = {chunk.chunk_id: chunk for chunk in current}
        fingerprints.append(corpus_fingerprint(chunk_index))
        if embedder is None:
            index = BM25Index(current)
            rebuilt = True
        else:
            from gamerag.retrieval.dense import DenseIndex

            index = DenseIndex(current, embedder, workspace / "index")
            rebuilt = index.rebuilt
        pipeline = Pipeline({"revision_fixture": index}, top_k=1,
                            retriever_name="bm25" if embedder is None else "dense")
        row = run_case(pipeline, cases[revision["case_id"]], profile, chunk_index, None)
        evidence = row.get("final_evidence", [])
        correct_revision = bool(evidence) and all(doc["version"] == f"revid:{revision['revid']}" for doc in evidence)
        row.update(expected_revision=revision["revid"], index_rebuilt=rebuilt,
                   expected_text=revision["expected"], forbidden_text=revision["forbidden"],
                   corpus_sha256=fingerprints[-1],
                   passed=(not row.get("error") and revision["expected"] in row.get("answer", "")
                           and revision["forbidden"] not in row.get("answer", "") and correct_revision
                           and bool(row.get("citations")) and rebuilt))
        rows.append(row)
    distinct = len(set(fingerprints)) == len(fingerprints)
    return {"schema_version": 2,
            "run": {**run_metadata(settings, label="synthetic-document-revisions", dataset=bank_path),
                    "fixture_sha256": file_hash(fixture_path), "synthetic": True,
                    "retriever": "bm25" if embedder is None else "dense", "generator": "extractive",
                    "same_persist_path": True, "n_cases": len(rows)},
            "overall": {**_agg(rows), "passed": sum(row["passed"] for row in rows),
                        "corpus_fingerprints_changed": distinct,
                        "all_passed": all(row["passed"] for row in rows) and distinct}, "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dense", action="store_true")
    args = parser.parse_args()
    base = get_settings()
    settings = Settings(root=base.root, profile="base", generator="extractive",
                        retriever="dense" if args.dense else "bm25", llm_offline=True)
    embedder = None
    if args.dense:
        from gamerag.retrieval.embeddings import get_embedder

        embedder = get_embedder(settings.embedding_model, str(settings.path(settings.models_dir)))
    scratch = settings.root / ".pytest_cache"
    scratch.mkdir(exist_ok=True)
    # Chroma conserva handles mmap en Windows; una limpieza parcial no invalida la medición.
    with TemporaryDirectory(prefix="document-revisions-", dir=scratch, ignore_cleanup_errors=True) as temporary:
        Path(temporary).resolve().relative_to(scratch.resolve())
        report = run_revisions(settings, Path(temporary), embedder=embedder)
    report["run"]["temporary_workspace_removed"] = not Path(temporary).exists()
    path = write_report(settings.root / "eval" / "results", "versions", report)
    print(json.dumps(report["overall"], indent=2))
    print(f"-> {path}")
    if not report["overall"]["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
