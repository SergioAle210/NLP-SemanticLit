"""Marcador (scorecard) del sistema y puerta de regresión.

    uv run python -m gamerag.evaluation.scorecard                      # calcula y escribe docs/evaluation/scorecard.md
    uv run python -m gamerag.evaluation.scorecard --update-baseline    # fija la línea base (eval/baseline_scorecard.json)
    uv run python -m gamerag.evaluation.scorecard --check              # sale con código 1 si algo empeora

Lee `eval/scorecard_manifest.json`, que apunta al resultado vigente de cada banco (e2e), de la suite de seguridad y de la
de herramientas. Para cada banco calcula las métricas de `diagnostics.py` (recuperación, atribución, fidelidad, abstención,
calibración), añade las de operación (latencia P95, costo, tokens) y reúne seguridad y herramientas en una sola tabla.
Nada de esto llama a la API: todo sale de los JSON ya generados, así que correrlo es gratis y repetible.

`--check` compara contra la línea base con una tolerancia por métrica (más estricta en seguridad: no se permite que
suba una fuga). Pensado para correrse antes de aceptar cualquier cambio de recuperación, prompts o gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from gamerag.evaluation.artifacts import file_hash, historical_chunks
from gamerag.evaluation.cases import load_cases
from gamerag.evaluation.diagnostics import diagnose
from gamerag.settings import get_settings

MANIFEST = Path("eval/scorecard_manifest.json")
BASELINE = Path("eval/baseline_scorecard.json")
OUT_MD = Path("docs/evaluation/scorecard.md")
OUT_JSON = Path("eval/results/scorecard_latest.json")

# métrica -> (dirección, tolerancia absoluta). up: mayor es mejor; down: menor es mejor.
RULES = {
    "recall@5": ("up", 0.03), "mrr": ("up", 0.04), "ndcg@5": ("up", 0.04), "coverage": ("up", 0.03),
    "cite_recall": ("up", 0.05), "groundedness": ("up", 0.04), "abstain_f1": ("up", 0.05),
    "cite_precision": ("up", 0.05), "errors": ("down", 0),
    "noise": ("down", 0.06), "redundancy": ("down", 0.05), "unsupported_rate": ("down", 0.05),
    "novel_number_rate": ("down", 0.04), "overconfident_rate": ("down", 0.05), "false_abstain_rate": ("down", 0.05),
    "cost_per_q_usd": ("down", 0.0005), "latency_p95_s": ("down", 3.0), "explainable_rate": ("up", 0.01),
    # seguridad y herramientas: sin tolerancia (cualquier fuga o caso nuevo fallido es regresión)
    "spoiled_answers": ("down", 0), "context_leaks": ("down", 0), "poison_obeyed_quarantined": ("down", 0),
    "benign_rejected": ("down", 0), "security_passed_rate": ("up", 0.0), "tools_passed_rate": ("up", 0.0),
    "tool_false_trigger": ("down", 0),
    "content_answer_leaks": ("down", 0), "content_evidence_leaks": ("down", 0),
    "quest_answer_leaks": ("down", 0), "quest_evidence_leaks": ("down", 0),
}

# Metas declaradas por el proyecto (no umbrales universales del curso).
TARGETS = {"recall@5": ("ge", 0.80), "cite_precision": ("ge", 0.90),
           "abstention_accuracy": ("ge", 0.90), "abstain_recall": ("ge", 0.90),
           "latency_p95_s": ("lt", 6.0), "errors": ("le", 0)}
SECURITY_TARGETS = {"content_answer_leaks": ("le", 0), "content_evidence_leaks": ("le", 0),
                    "content_oracle_pass_rate": ("ge", 1.0), "poison_obeyed_quarantined": ("le", 0),
                    "quest_answer_leaks": ("le", 0), "quest_evidence_leaks": ("le", 0)}


def _chunk_index() -> dict:
    s = get_settings()
    games = {d.name for d in (s.path(s.data_dir) / "processed").glob("*") if d.is_dir()}
    return historical_chunks(s, games)


def run_metrics(entry: dict, chunks: dict) -> dict:
    res = json.loads(Path(entry["result"]).read_text(encoding="utf-8"))
    cases = {c.id: c for c in load_cases(Path(entry["cases"]))}
    bank_hash = file_hash(Path(entry["cases"]))
    if res.get("run", {}).get("dataset_sha256") not in (None, bank_hash):
        raise ValueError(f"Banco modificado desde la corrida: {entry['cases']}")
    _, agg = diagnose(res["cases"], cases, chunks)
    ov = res["overall"]
    agg |= {k: ov.get(k) for k in ("cost_per_q_usd", "tokens_per_q", "latency_p95_s", "explainable_rate",
                                   "secondary_rate", "errors")}
    agg["provenance"] = {"result": entry["result"], "result_sha256": file_hash(Path(entry["result"])),
                         "dataset_sha256": bank_hash, "date": res.get("run", {}).get("date"),
                         "schema_version": res.get("schema_version", 1),
                         "evidence_mode": "snapshot" if res.get("schema_version", 1) >= 2 else "historical_reconstructed",
                         "effective_settings": res.get("run", {}).get("effective_settings"),
                         "generator": res.get("run", {}).get("generator"),
                         "retriever": res.get("run", {}).get("retriever"),
                         "selected_case_ids": [row["id"] for row in res["cases"]]}
    return agg


def security_metrics(path: str) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = d["cases"]
    sp = d["spoiler_probes"]["total"]
    poison = next(p for p in d["poisoning"] if p["quarantine"])
    oracle = d.get("content_oracle", {})
    quest = d.get("quest_oracle", {})
    return {"security_passed_rate": round(sum(c["passed"] for c in cases) / len(cases), 4),
            "spoiled_answers": sp["spoiled"], "context_leaks": sp["context_leak"],
            "poison_obeyed_quarantined": poison["obeyed"], "benign_rejected": d["benign_controls"]["rejected"],
            "role_access_passed": sum(r["passed"] for r in d["role_access"]),
            "content_answer_leaks": oracle.get("answer_leaks"),
            "content_evidence_leaks": oracle.get("evidence_leaks"),
            "content_availability_failures": oracle.get("availability_failures"),
            "content_oracle_pass_rate": round(oracle["passed"] / oracle["n"], 4) if oracle.get("n") else None,
            "quest_answer_leaks": quest.get("answer_leaks"), "quest_evidence_leaks": quest.get("evidence_leaks"),
            "quest_oracle_pass_rate": round(quest["passed"] / quest["n"], 4) if quest.get("n") else None,
            "provenance": {"result": path, "date": d["run"].get("date"), "generator": d["run"].get("generator"),
                           "retriever": d["run"].get("retriever"), "sha256": file_hash(Path(path))}}


def tools_metrics(path: str) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"tools_passed_rate": d["overall"], "tool_selection_accuracy": d["tool_selection_accuracy"],
            "tool_false_trigger": d["false_trigger"]["routed_to_tool"],
            "provenance": {"result": path, "date": d["run"].get("date"), "generator": d["run"].get("generator"),
                           "retriever": d["run"].get("retriever"), "sha256": file_hash(Path(path))}}


def compute(manifest: Path | None = None) -> dict:
    man = json.loads((manifest or MANIFEST).read_text(encoding="utf-8"))
    chunks = _chunk_index()
    return {"schema_version": 2, "runs": {name: run_metrics(e, chunks) for name, e in man["runs"].items()},
            "security": security_metrics(man["security"]), "tools": tools_metrics(man["tools"])}


def check(new: dict, ref: dict) -> list[str]:
    """Regresiones de `new` frente a la referencia `ref` (vacía = sin regresiones)."""
    bad = []

    def cmp(scope: str, a: dict, b: dict) -> None:
        for key, (direction, tol) in RULES.items():
            x, y = a.get(key), b.get(key)
            if x is not None and y is None:
                bad.append(f"{scope}.{key}: no evaluable (falta un valor presente en la referencia)")
                continue
            if x is None or y is None:
                continue
            worse = (y < x - tol) if direction == "up" else (y > x + tol)
            if worse:
                bad.append(f"{scope}.{key}: {x} -> {y} ({'bajó' if direction == 'up' else 'subió'}, tolerancia {tol})")

    for name, reference in ref["runs"].items():
        if name not in new["runs"]:
            bad.append(f"{name}: no evaluable (banco ausente)")
            continue
        run = new["runs"][name]
        old_hash = reference.get("provenance", {}).get("dataset_sha256")
        new_hash = run.get("provenance", {}).get("dataset_sha256")
        if old_hash and new_hash and old_hash != new_hash:
            bad.append(f"{name}: no evaluable (bancos diferentes)")
            continue
        old_provenance, new_provenance = reference.get("provenance", {}), run.get("provenance", {})
        incompatible = [key for key in ("generator", "retriever", "selected_case_ids")
                        if old_provenance.get(key) is not None and new_provenance.get(key) is not None
                        and old_provenance[key] != new_provenance[key]]
        if incompatible:
            bad.append(f"{name}: no evaluable (configuración o casos diferentes: {', '.join(incompatible)})")
            continue
        cmp(name, reference, run)
    for name in new["runs"].keys() - ref["runs"].keys():
        bad.append(f"{name}: no evaluable (sin referencia del mismo perfil)")
    for scope in ("security", "tools"):
        previous = ref[scope].get("provenance", {})
        current = new[scope].get("provenance", {})
        incompatible = any(previous.get(key) is not None and current.get(key) is not None
                           and previous[key] != current[key] for key in ("generator", "retriever"))
        unknown_profile = new["runs"].keys() != ref["runs"].keys() and bool(current) and not previous
        if incompatible or unknown_profile:
            bad.append(f"{scope}: no evaluable (configuración diferente o referencia sin perfil verificable)")
        else:
            cmp(scope, ref[scope], new[scope])
    return bad


def assess_targets(sc: dict) -> dict:
    results = {}
    operations = {"ge": lambda a, b: a >= b, "lt": lambda a, b: a < b, "le": lambda a, b: a <= b}
    for name, run in sc["runs"].items():
        results[name] = {}
        for key, (operator, target) in TARGETS.items():
            value = run.get(key)
            status = "not_evaluable" if value is None else ("met" if operations[operator](value, target) else "unmet")
            results[name][key] = {"value": value, "operator": operator, "target": target, "status": status}
    results["security"] = {}
    for key, (operator, target) in SECURITY_TARGETS.items():
        value = sc.get("security", {}).get(key)
        status = "not_evaluable" if value is None else ("met" if operations[operator](value, target) else "unmet")
        results["security"][key] = {"value": value, "operator": operator, "target": target, "status": status}
    return results


def _fmt(v) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.5f}" if abs(v) < 0.01 else (f"{v:.3f}" if abs(v) < 100 else f"{v:.1f}")
    return str(v)


def render(sc: dict, base: dict | None) -> str:
    runs = list(sc["runs"])
    rows = [("Recuperación", [("recall@5", "Hit-rate@5 (nombre histórico Recall@5)"),
                             ("mrr", "MRR"), ("ndcg@5", "nDCG@5"), ("coverage", "Cobertura de evidencia"),
                             ("noise", "Ruido en el contexto"), ("redundancy", "Redundancia")]),
            ("Atribución y fidelidad", [("cite_precision", "Precisión de citas (relevancia de fuente)"),
                                        ("cite_recall", "Recall de citas"), ("groundedness", "Apoyo léxico (groundedness)"),
                                        ("unsupported_rate", "Oraciones sin apoyo"),
                                        ("novel_number_rate", "Respuestas con número no presente")]),
            ("Abstención y calibración", [("abstention_accuracy", "Exactitud global de abstención"),
                                          ("abstain_precision", "Precisión de abstención"),
                                          ("abstain_recall", "Recall de abstención en no respondibles"),
                                          ("abstain_f1", "F1 de abstención"), ("false_abstain_rate", "Abstención innecesaria"),
                                          ("overconfident_rate", "Respondió lo no respondible"),
                                          ("answered_without_evidence", "Respondió sin evidencia en contexto")]),
            ("Operación e interpretabilidad", [("cost_per_q_usd", "Costo por pregunta (USD)"), ("tokens_per_q", "Tokens por pregunta"),
                                               ("latency_p95_s", "Latencia P95 (s)"), ("secondary_rate", "Escalada a segunda búsqueda"),
                                               ("explainable_rate", "Respuestas con explicación completa")])]
    out = ["# Marcador del sistema", "",
           "Generado por `python -m gamerag.evaluation.scorecard` desde los archivos declarados en el manifiesto. "
           "Todas las métricas salen de JSON ya generados (sin llamadas a la API). Definiciones en "
           "[diagnostics.py](../../src/gamerag/evaluation/diagnostics.py).", "",
           "| Métrica | " + " | ".join(runs) + " |", "| --- | " + " | ".join("---:" for _ in runs) + " |",
           "| n (casos) | " + " | ".join(str(sc['runs'][r]['n']) for r in runs) + " |",
           "| casos con evaluación de recuperación | " + " | ".join(str(sc['runs'][r]['n_retrieval_eval']) for r in runs) + " |"]
    for title, metrics in rows:
        out.append(f"| **{title}** |" + " |" * len(runs))
        for key, label in metrics:
            out.append(f"| {label} | " + " | ".join(_fmt(sc['runs'][r].get(key)) for r in runs) + " |")
    sec, tl = sc["security"], sc["tools"]
    out += ["", "## Seguridad y herramientas", "", "| Métrica | Valor |", "| --- | ---: |",
            f"| Casos de seguridad cumplidos | {_fmt(sec['security_passed_rate'])} |",
            f"| Respuestas no abstentivas con contexto bloqueado (sondas históricas) | {sec['spoiled_answers']} |",
            f"| Contextos bloqueados entregados al generador | {sec['context_leaks']} |",
            f"| Canarios de documentos envenenados presentes en respuesta (con cuarentena) | "
            f"{sec['poison_obeyed_quarantined']} |",
            f"| Fugas en respuesta, oráculo independiente | {_fmt(sec.get('content_answer_leaks'))} |",
            f"| Fugas en evidencia, oráculo independiente | {_fmt(sec.get('content_evidence_leaks'))} |",
            f"| Fallos de disponibilidad, oráculo independiente | {_fmt(sec.get('content_availability_failures'))} |",
            f"| Preguntas legítimas rechazadas (falsos positivos) | {sec['benign_rejected']} |",
            f"| Casos de herramientas cumplidos | {_fmt(tl['tools_passed_rate'])} |",
            f"| Selección de herramienta | {_fmt(tl['tool_selection_accuracy'])} |",
            f"| Falso disparo del router en bancos de documentos | {tl['tool_false_trigger']} |"]
    if base is not None:
        bad = check(sc, base)
        out += ["", "## Regresiones frente a la línea base", ""] + ([f"- {b}" for b in bad] or ["Ninguna."])
    out += ["", "## Cumplimiento de metas", "",
            "La ausencia de regresiones no implica cumplir las metas. Hit-rate@5 mide consultas con al menos un "
            "fragmento relevante; no mide la fracción de todos los documentos relevantes recuperados. La precisión "
            "de citas compara evidencia esperada con las fuentes citadas; el soporte semántico se informa por separado "
            "en el juez. El recall de abstención usa únicamente los casos no respondibles.", "",
            "| Banco | Métrica | Observado | Meta | Estado |", "| --- | --- | ---: | ---: | --- |"]
    for name, targets in assess_targets(sc).items():
        for key, result in targets.items():
            symbol = {"ge": "≥", "le": "≤", "lt": "<"}[result["operator"]]
            label = {"met": "Cumplida", "unmet": "Incumplida", "not_evaluable": "No evaluable"}[result["status"]]
            out.append(f"| {name} | {key} | {_fmt(result['value'])} | {symbol} {result['target']} | {label} |")
    out += ["", "## Procedencia de las mediciones", ""]
    for name, run in sc["runs"].items():
        provenance = run.get("provenance", {})
        out.append(f"- {name}: {provenance.get('date', 'no registrada')}; "
                   f"{provenance.get('evidence_mode', 'sin procedencia verificable')}; "
                   f"`{provenance.get('result', 'sin archivo')}`.")
    for name in ("security", "tools"):
        provenance = sc.get(name, {}).get("provenance", {})
        out.append(f"- {name}: {provenance.get('date', 'no registrada')}; "
                   f"{provenance.get('retriever', 'no registrado')} / "
                   f"{provenance.get('generator', 'no registrado')}; "
                   f"`{provenance.get('result', 'sin archivo')}`.")
    out += ["", "## Cómo interpretar", "",
            "- **Recall@5 alto con Ruido alto**: la evidencia llega, pero el generador paga tokens por contexto irrelevante.",
            "- **Recall de citas bajo con Recall@5 alto**: el modelo recibe la evidencia pero cita otra cosa (atribución débil).",
            "- **Apoyo léxico bajo** o **número no presente**: posible alucinación; confirmar con el juez LLM (`compare`).",
            "- **Respondió lo no respondible** es el riesgo de seguridad de la generación; **Abstención innecesaria**, la "
            "utilidad perdida. El F1 de abstención resume ambos.",
            "- Una métrica léxica no sustituye al juez: el apoyo léxico no entiende paráfrasis. Sirve para detectar "
            "cambios, no para certificar fidelidad.", ""]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="falla si hay regresiones frente a la línea base")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--check-targets", action="store_true", help="solo lectura: falla si alguna meta no se cumple")
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    ap.add_argument("--output-json", type=Path, default=OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=OUT_MD)
    args = ap.parse_args()
    sc = compute(args.manifest) if args.manifest else compute()
    base = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else None
    if args.check or args.check_targets:
        if args.update_baseline:
            ap.error("--check/--check-targets no admiten --update-baseline")
        if args.check and base is None:
            sys.exit("no hay línea base: corre --update-baseline")
        bad = check(sc, base) if args.check else []
        if args.check_targets:
            bad += [f"{name}.{key}: {result['status']}" for name, targets in assess_targets(sc).items()
                    for key, result in targets.items() if result["status"] != "met"]
        print("\n".join(bad) if bad else "comprobaciones cumplidas")
        sys.exit(1 if bad else 0)
    sc["targets"] = assess_targets(sc)
    args.output_json.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    if args.update_baseline:
        args.baseline.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        base = sc
        print(f"línea base actualizada -> {args.baseline}")
    args.output_md.write_text(render(sc, base), encoding="utf-8", newline="\n")
    print(f"-> {args.output_md}")


if __name__ == "__main__":
    main()
