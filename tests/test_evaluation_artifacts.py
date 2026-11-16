"""La evaluación inspecciona evidencia exacta, preserva procedencia y aísla solicitudes concurrentes."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import numpy as np
import pytest

from gamerag.evaluation import scorecard
from gamerag.evaluation.artifacts import (
    corpus_fingerprint,
    evidence_chunks,
    historical_chunks,
    run_metadata,
    text_hash,
    usage_from_calls,
    validate_case_rows,
    write_report,
)
from gamerag.evaluation.cases import EvalCase, load_cases
from gamerag.evaluation.compare import enrich, validate_pair
from gamerag.evaluation.diagnostics import aggregate, case_diagnostics
from gamerag.evaluation.e2e import run_case
from gamerag.evaluation.spoiler_oracle import observe_content
from gamerag.evaluation.versions import run_revisions
from gamerag.ingest.models import Chunk, Location
from gamerag.progress.models import Profile
from gamerag.schemas import Answer
from gamerag.settings import Settings
from gamerag.telemetry import record_call

ROOT = Path(__file__).resolve().parents[1]


def chunk(cid="c", text="The training key is on shelf A.", **overrides):
    data = dict(chunk_id=cid, text=text, source="S", page=0, version="revid:1", url="u", section="s",
                sections=["s"], hash=text_hash(text), chunker="structural", n_words=len(text.split()), game="g")
    return Chunk(**(data | overrides))


def case(cid="case"):
    return EvalCase(id=cid, question="Where is the training key?", expected_behavior="Answer shelf A.",
                    expected_sources=["S"], expected_pages=[0], answerable=True, risk_level="low",
                    category="direct", game="g", profile="p", evidence=[["shelf A"]])


def row(text="The training key is on shelf A."):
    return {"id": "case", "game": "g", "question": "Where is the training key?", "answerable": True,
            "context": ["c"], "sources": ["c"], "citations": [{"chunk_id": "c", "source": "S", "page": 0}],
            "answer": "The training key is on shelf A.", "abstained": False,
            "final_evidence": [{"chunk_id": "c", "source": "S", "page": 0, "text": text, "version": "revid:1",
                                "url": "u", "section": "s", "source_hash": text_hash("hidden full document"),
                                "is_excerpt": True, "evidence_hash": text_hash(text)}]}


def test_snapshot_never_recovers_hidden_text_from_same_id():
    result = row("Only the training room is visible.")
    original = chunk(text="The training key is on shelf A. Hidden late-game secrets.")
    snapshot = evidence_chunks(result, {"c": original})[0]
    assert snapshot.text == "Only the training room is visible."
    assert snapshot.hash == text_hash(snapshot.text) and snapshot.is_excerpt
    assert snapshot.source_hash == result["final_evidence"][0]["source_hash"]
    diagnostics = case_diagnostics(case(), result, {"c": original})
    assert diagnostics["coverage"] == 0 and diagnostics["cite_precision"] == 0


def test_snapshot_hash_citation_triple_and_missing_ids_fail_closed():
    result = row()
    result["final_evidence"][0]["evidence_hash"] = "invalid"
    with pytest.raises(ValueError, match="hash"):
        evidence_chunks(result, {})
    result = row()
    result["citations"][0]["page"] = 9
    with pytest.raises(ValueError, match="cita ajena"):
        evidence_chunks(result, {}, cited=True)
    with pytest.raises(ValueError, match="históricos"):
        evidence_chunks({"id": "legacy", "context": ["unknown"]}, {})
    result = row()
    result["context"] = []
    with pytest.raises(ValueError, match="no coinciden"):
        evidence_chunks(result, {})


def test_e2e_records_invalid_evidence_as_failed_case():
    class InvalidEvidencePipeline:
        def ask(self, question, game, profile):
            return Answer(answer="Text", abstained=False, game=game, trace_id="t",
                          sources=[{"chunk_id": "missing", "source": "S", "page": 0}]), SimpleNamespace(
                context=["missing"], final_evidence=[])

    result = run_case(InvalidEvidencePipeline(), case(), Profile(user_id="p", role="player"), {}, None)
    assert result["error"].startswith("EvidenceContractError:")
    assert result["final_answer"]["answer"] == "Text"


def test_historical_loader_includes_secondary_and_notes(tmp_path):
    settings = Settings(root=tmp_path, _env_file=None)
    for rel, cid in (("data/processed/g/chunks.structural.jsonl", "primary"),
                     ("data/processed/g/chunks.structural-multi.jsonl", "secondary"),
                     ("data/memory/g/notes.jsonl", "note")):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(chunk(cid=cid).model_dump_json() + "\n", encoding="utf-8")
    assert set(historical_chunks(settings, {"g"})) == {"primary", "secondary", "note"}


def test_case_bank_and_pair_mismatch_are_not_silently_omitted():
    with pytest.raises(ValueError, match="ajenos"):
        validate_case_rows([{"id": "other"}], {"case": case()})
    with pytest.raises(ValueError, match="question"):
        validate_case_rows([{"id": "case", "question": "Changed question"}], {"case": case()})
    with pytest.raises(ValueError, match="mismos IDs"):
        validate_pair([{"id": "a"}], [{"id": "b"}])


def test_metadata_is_safe_and_writes_are_unique(tmp_path):
    settings = Settings(root=tmp_path, anthropic_api_key="private-key-never-export", _env_file=None)
    metadata = run_metadata(settings, label="test", chunks={"c": chunk()})
    assert "private-key" not in json.dumps(metadata) and "anthropic_api_key" not in metadata["effective_settings"]
    assert metadata["configuration_sha256"].startswith("sha256:")
    assert metadata["implementation_sha256"].startswith("sha256:")
    report = {"run": metadata, "cases": []}
    out = write_report(tmp_path, "test", report)
    with pytest.raises(FileExistsError):
        write_report(tmp_path, "test", report)
    assert json.loads(out.read_text(encoding="utf-8"))["cases"] == []


def test_corpus_identity_changes_for_metadata_even_with_identical_text():
    original = chunk()
    version = original.model_copy(update={"version": "revid:2"})
    restricted = original.model_copy(update={"location": Location(restricted=True)})
    assert len({corpus_fingerprint({"c": value}) for value in [original, version, restricted]}) == 3


def test_request_usage_separates_attempts_cache_and_unknown_cost():
    calls = [{"status": "error", "attempt": 1, "retry": True, "usage_known": False},
             {"status": "ok", "attempt": 2, "input_tokens": 20, "output_tokens": 4, "cost_usd": 0.1,
              "usage_known": True}, {"status": "cache_hit", "attempt": 0, "cached": True, "usage_known": True}]
    usage = usage_from_calls(calls)
    assert usage["http_call_count"] == 2 and usage["http_retry_count"] == 1
    assert usage["llm_cached_calls"] == 1 and usage["usage_unknown_calls"] == 1
    assert usage["cost_usd"] == 0.1 and usage["input_tokens"] == 20


def test_concurrent_failures_keep_only_their_own_usage():
    barrier = Barrier(2)

    class BrokenPipeline:
        def ask(self, question, game, profile):
            record_call(status="ok", attempt=1, input_tokens=int(profile.user_id[-1]), output_tokens=0,
                        cost_usd=0.01, usage_known=True)
            barrier.wait(timeout=5)
            raise RuntimeError("expected failure after provider call")

    class SharedLedger:
        def summary(self):
            raise AssertionError("The shared ledger must not measure individual requests")

    def run(index):
        return run_case(BrokenPipeline(), case(), Profile(user_id=f"p{index}", role="player"), {}, SharedLedger())

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, [1, 2]))
    assert [result["input_tokens"] for result in results] == [1, 2]
    assert len({result["trace_id"] for result in results}) == 2
    assert all(result["error"] and len(result["llm_calls"]) == 1 for result in results)


class JudgeStub:
    def complete(self, messages, **kwargs):
        self.payload = json.loads(messages[0]["content"])
        record_call(status="ok", attempt=1, input_tokens=12, output_tokens=6, cost_usd=0.001, usage_known=True)
        return json.dumps({"verdict": "correct", "faithfulness": "unsupported", "covered_parts": [],
                           "supported_citation_ids": [], "rationale": "The visible evidence does not state shelf A."})

    def text(self, message):
        return message


def test_judge_receives_exact_evidence_and_separates_correctness_from_support():
    llm = JudgeStub()
    result = enrich([row("Only the training room is visible.")], {"case": case()}, {"c": chunk()}, llm)[0]
    assert llm.payload["authorized_final_evidence"][0]["text"] == "Only the training room is visible."
    assert result["correct"] == 1.0 and result["faithfulness_score"] == 0.0
    assert result["citation_support_precision"] == 0.0 and result["factual_coverage"] == 0.0
    assert result["judge_usage"]["input_tokens"] == 12 and result["judge_input"] == llm.payload


def test_judge_failure_is_recorded_without_fabricated_score():
    class BrokenJudge(JudgeStub):
        def text(self, message):
            return "invalid json"

    result = enrich([row()], {"case": case()}, {}, BrokenJudge())[0]
    assert result["judge_error"] and result["correct"] is None
    assert result["judge_usage"]["input_tokens"] == 12


def test_diagnostics_exposes_true_denominators_and_legacy_alias():
    diagnostic = case_diagnostics(case(), row(), {})
    metrics = aggregate([diagnostic])
    assert metrics["hit_rate@5"] == metrics["recall@5"] == 1
    assert metrics["abstention_counts"] == {"tp": 0, "fp": 0, "fn": 0, "tn": 1,
                                             "answerable": 1, "unanswerable": 0, "errors_excluded": 0}
    assert metrics["abstain_recall"] is None and metrics["abstention_accuracy"] == 1


def test_scorecard_check_is_read_only(tmp_path, monkeypatch):
    data = {"runs": {"r": {"recall@5": 1.0}}, "security": {}, "tools": {}}
    baseline, output, markdown = [tmp_path / name for name in ("baseline.json", "output.json", "out.md")]
    baseline.write_text(json.dumps(data), encoding="utf-8")
    output.write_text("original json", encoding="utf-8")
    markdown.write_text("original markdown", encoding="utf-8")
    monkeypatch.setattr(scorecard, "compute", lambda: data)
    monkeypatch.setattr(scorecard, "BASELINE", baseline)
    monkeypatch.setattr(scorecard, "OUT_JSON", output)
    monkeypatch.setattr(scorecard, "OUT_MD", markdown)
    monkeypatch.setattr("sys.argv", ["scorecard", "--check"])
    with pytest.raises(SystemExit) as exit_result:
        scorecard.main()
    assert exit_result.value.code == 0
    assert output.read_text() == "original json" and markdown.read_text() == "original markdown"


def test_regression_pass_does_not_imply_target_pass_or_missing_metric_success():
    data = {"runs": {"r": {"recall@5": 0.95, "cite_precision": 0.7}}, "security": {}, "tools": {}}
    assert scorecard.check(data, data) == []
    targets = scorecard.assess_targets(data)["r"]
    assert targets["recall@5"]["status"] == "met" and targets["cite_precision"]["status"] == "unmet"
    assert targets["abstain_recall"]["status"] == "not_evaluable"
    assert scorecard.check({"runs": {"r": {}}, "security": {}, "tools": {}}, data)


def test_independent_oracle_catches_content_even_if_context_was_authorized():
    probe = {"forbidden_patterns": ["woman standing behind"], "required_patterns": []}
    result = observe_content(probe, "The battle ends.", [{"text": "A woman standing behind Ryu appears."}])
    assert not result["passed"] and result["evidence_leaks"] and not result["answer_leaks"]


def test_security_report_preserves_mixed_expectations_within_one_vector():
    from gamerag.evaluation.security_report import render

    guarded = json.loads((ROOT / "eval/results/20261116T022654688800Z-b171d853_security_guarded.json")
                         .read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "eval/results/20261116T022700230687Z-c9546ebd_security_baseline.json")
                          .read_text(encoding="utf-8"))
    # Rechazar la entrada y responder sin exponer el canario son criterios distintos.
    for cases in (guarded["cases"], list(reversed(guarded["cases"]))):
        markdown = render({**guarded, "cases": cases}, baseline)
        injection = markdown.split("### Inyección de instrucciones (directa)", 1)[1].split("\n### ", 1)[0]
        expected_summary = next(line for line in injection.splitlines()
                                if line.startswith("**Comportamientos esperados"))
        assert "`rejected_input`" in expected_summary and "`no_injection_effect`" in expected_summary
        rows = {line.split("|")[1].strip(): line.split("|") for line in injection.splitlines()
                if line.startswith("| sec_")}
        assert rows["sec_000"][3].strip() == "`rejected_input`"
        assert rows["sec_021"][3].strip() == "`no_injection_effect`"
        assert "outcome=answered" in rows["sec_021"][5]


def test_two_document_revisions_reingest_same_source_and_keep_both_results(tmp_path):
    report = run_revisions(Settings(root=ROOT, retriever="bm25", generator="extractive", _env_file=None), tmp_path)
    assert report["overall"]["all_passed"] and report["overall"]["passed"] == 2
    first, second = report["cases"]
    assert first["context"] == second["context"]
    assert first["final_evidence"][0]["version"] == "revid:101"
    assert second["final_evidence"][0]["version"] == "revid:102"
    assert first["corpus_sha256"] != second["corpus_sha256"]
    assert len(load_cases(ROOT / "eval/cases_versions.jsonl")) == 2


def test_dense_rebuilds_same_path_when_only_version_or_access_metadata_changes(tmp_path):
    pytest.importorskip("chromadb")
    from gamerag.retrieval.dense import DenseIndex

    class TinyEmbedder:
        model = SimpleNamespace(key="test-version-fixture")

        def embed_passages(self, texts):
            return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)

        def embed_query(self, text):
            return np.array([1.0, 0.0], dtype=np.float32)

    original = chunk()
    embedder = TinyEmbedder()
    assert DenseIndex([original], embedder, tmp_path).rebuilt
    assert not DenseIndex([original], embedder, tmp_path).rebuilt
    revised = original.model_copy(update={"version": "revid:2", "location": Location(restricted=True)})
    changed = DenseIndex([revised], embedder, tmp_path)
    assert changed.rebuilt and changed.search("key", 1)[0].chunk.version == "revid:2"
    stored = changed._col.get(include=["metadatas"])["metadatas"][0]
    assert stored["version"] == "revid:2" and stored["restricted"] is True
