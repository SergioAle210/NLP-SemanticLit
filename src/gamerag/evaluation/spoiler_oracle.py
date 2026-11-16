"""Sondas de contenido independientes de la política de producción y de su clasificación de chunks.

    python -m gamerag.evaluation.spoiler_oracle --serving-profile base --retriever bm25

Las expresiones prohibidas/permitidas se fijan en el banco. Nunca se deducen de LocationGate ni se
resta el contexto supuestamente autorizado: respuesta y evidencia se inspeccionan por separado.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from gamerag.evaluation.artifacts import run_metadata, write_report
from gamerag.games import load_all_games
from gamerag.pipeline import build_pipeline
from gamerag.progress.models import Profile, load_profiles
from gamerag.settings import Settings, get_settings
from gamerag.telemetry import request_scope

BANK = Path("eval/security_content_oracle_v2.jsonl")


def observe_content(case: dict, answer: str, evidence: list[dict]) -> dict:
    body = "\n".join(doc["text"] for doc in evidence)
    forbidden = case.get("forbidden_patterns", [])
    required = case.get("required_patterns", [])

    def matches(patterns, text):
        return [pattern for pattern in patterns if re.search(pattern, text, flags=re.I | re.S)]

    answer_leaks, evidence_leaks = matches(forbidden, answer), matches(forbidden, body)
    missing_answer = [pattern for pattern in required if pattern not in matches(required, answer)]
    missing_evidence = [pattern for pattern in required if pattern not in matches(required, body)]
    return {"answer_leaks": answer_leaks, "evidence_leaks": evidence_leaks,
            "missing_allowed_answer": missing_answer, "missing_allowed_evidence": missing_evidence,
            "passed": not (answer_leaks or evidence_leaks or missing_answer or missing_evidence)}


def run_oracle(pipe, profiles: dict, cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        template = profiles[case.get("profile", "novato")].model_dump(mode="json")
        template["progress"][case["game"]] = case["progress"]
        profile = Profile.model_validate(template)
        with request_scope() as capture:
            try:
                answer, trace = pipe.ask(case["question"], case["game"], profile)
                evidence = [doc.model_dump(mode="json") for doc in trace.final_evidence]
                row = {"id": case["id"], "game": case["game"], "question": case["question"],
                       "player_profile": profile.model_dump(mode="json"), "answer": answer.answer,
                       "abstained": answer.abstained, "final_evidence": evidence,
                       "citations": [source.model_dump(mode="json") for source in answer.sources],
                       "outcome": trace.outcome, "route": trace.route,
                       **observe_content(case, answer.answer, evidence), "error": None}
            except Exception as exc:  # noqa: BLE001 - una sonda fallida nunca se registra como segura
                row = {"id": case["id"], "passed": False, "error": f"{type(exc).__name__}: {exc}"}
        row.update(trace_id=capture.trace_id, llm_calls=list(capture.calls),
                   degradations=list(capture.degradations), stages=list(capture.stages))
        rows.append(row)
    return {"n": len(rows), "passed": sum(row["passed"] for row in rows),
            "answer_leaks": sum(bool(row.get("answer_leaks")) for row in rows),
            "evidence_leaks": sum(bool(row.get("evidence_leaks")) for row in rows),
            "availability_failures": sum(bool(row.get("missing_allowed_answer") or row.get("missing_allowed_evidence"))
                                         for row in rows),
            "errors": sum(bool(row.get("error")) for row in rows), "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serving-profile", choices=["base", "full"], default="base")
    parser.add_argument("--retriever", choices=["bm25", "dense", "hybrid"], default=None)
    parser.add_argument("--cases", default=str(BANK), help="v1 y v2 se conservan como bancos distintos")
    args = parser.parse_args()
    base = get_settings()
    options = {"root": base.root, "profile": args.serving_profile, "only_games": ["zelda1", "ninja_gaiden_nes"]}
    if args.retriever:
        options["retriever"] = args.retriever
    settings = Settings(**options)
    games = load_all_games(settings.path(settings.games_config_dir))
    profiles = load_profiles(settings.path(settings.seed_profiles), games)
    bank_path = settings.root / args.cases
    cases = [json.loads(line) for line in bank_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    result = run_oracle(build_pipeline(settings), profiles, cases)
    report = {"schema_version": 2,
              "run": {**run_metadata(settings, label="content-oracle", dataset=bank_path),
                      "oracle": "independent_predeclared_content_patterns", "generator": settings.generator,
                      "oracle_bank": args.cases, "oracle_version": cases[0].get("oracle_version", 1),
                      "retriever": settings.retriever}, "overall": {k: v for k, v in result.items() if k != "cases"},
              "cases": result["cases"]}
    path = write_report(settings.root / "eval" / "results", "oracle", report)
    print(json.dumps(report["overall"], indent=2))
    print(f"-> {path}")
    if result["passed"] != result["n"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
