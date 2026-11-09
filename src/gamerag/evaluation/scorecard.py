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

from gamerag.evaluation.cases import load_cases
from gamerag.evaluation.diagnostics import diagnose
from gamerag.retrieval.bm25 import load_chunks
from gamerag.settings import get_settings

MANIFEST = Path("eval/scorecard_manifest.json")
BASELINE = Path("eval/baseline_scorecard.json")
OUT_MD = Path("docs/evaluation/scorecard.md")
OUT_JSON = Path("eval/results/scorecard_latest.json")

# métrica -> (dirección, tolerancia absoluta). up: mayor es mejor; down: menor es mejor.
RULES = {
    "recall@5": ("up", 0.03), "mrr": ("up", 0.04), "ndcg@5": ("up", 0.04), "coverage": ("up", 0.03),
    "cite_recall": ("up", 0.05), "groundedness": ("up", 0.04), "abstain_f1": ("up", 0.05),
    "noise": ("down", 0.06), "redundancy": ("down", 0.05), "unsupported_rate": ("down", 0.05),
    "novel_number_rate": ("down", 0.04), "overconfident_rate": ("down", 0.05), "false_abstain_rate": ("down", 0.05),
    "cost_per_q_usd": ("down", 0.0005), "latency_p95_s": ("down", 3.0), "explainable_rate": ("up", 0.01),
    # seguridad y herramientas: sin tolerancia (cualquier fuga o caso nuevo fallido es regresión)
    "spoiled_answers": ("down", 0), "context_leaks": ("down", 0), "poison_obeyed_quarantined": ("down", 0),
    "benign_rejected": ("down", 0), "security_passed_rate": ("up", 0.0), "tools_passed_rate": ("up", 0.0),
    "tool_false_trigger": ("down", 0),
}


def _chunk_index() -> dict:
    s = get_settings()
    out: dict = {}
    for d in sorted((s.path(s.data_dir) / "processed").glob("*")):
        f = d / f"chunks.{s.chunker}-multi.jsonl"
        f = f if f.exists() else d / f"chunks.{s.chunker}.jsonl"
        if f.exists():
            out.update({c.chunk_id: c for c in load_chunks(f)})
    return out


def run_metrics(entry: dict, chunks: dict) -> dict:
    res = json.loads(Path(entry["result"]).read_text(encoding="utf-8"))
    cases = {c.id: c for c in load_cases(Path(entry["cases"]))}
    _, agg = diagnose(res["cases"], cases, chunks)
    ov = res["overall"]
    agg |= {k: ov.get(k) for k in ("cost_per_q_usd", "tokens_per_q", "latency_p95_s", "explainable_rate",
                                   "secondary_rate", "errors")}
    return agg


def security_metrics(path: str) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = d["cases"]
    sp = d["spoiler_probes"]["total"]
    poison = next(p for p in d["poisoning"] if p["quarantine"])
    return {"security_passed_rate": round(sum(c["passed"] for c in cases) / len(cases), 4),
            "spoiled_answers": sp["spoiled"], "context_leaks": sp["context_leak"],
            "poison_obeyed_quarantined": poison["obeyed"], "benign_rejected": d["benign_controls"]["rejected"],
            "role_access_passed": sum(r["passed"] for r in d["role_access"])}


def tools_metrics(path: str) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return {"tools_passed_rate": d["overall"], "tool_selection_accuracy": d["tool_selection_accuracy"],
            "tool_false_trigger": d["false_trigger"]["routed_to_tool"]}


def compute() -> dict:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks = _chunk_index()
    return {"runs": {name: run_metrics(e, chunks) for name, e in man["runs"].items()},
            "security": security_metrics(man["security"]), "tools": tools_metrics(man["tools"])}


def check(new: dict, ref: dict) -> list[str]:
    """Regresiones de `new` frente a la referencia `ref` (vacía = sin regresiones)."""
    bad = []

    def cmp(scope: str, a: dict, b: dict) -> None:
        for key, (direction, tol) in RULES.items():
            x, y = a.get(key), b.get(key)
            if x is None or y is None:
                continue
            worse = (y < x - tol) if direction == "up" else (y > x + tol)
            if worse:
                bad.append(f"{scope}.{key}: {x} -> {y} ({'bajó' if direction == 'up' else 'subió'}, tolerancia {tol})")

    for name, run in new["runs"].items():
        if name in ref["runs"]:
            cmp(name, ref["runs"][name], run)
    cmp("security", ref["security"], new["security"])
    cmp("tools", ref["tools"], new["tools"])
    return bad


def _fmt(v) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.5f}" if abs(v) < 0.01 else (f"{v:.3f}" if abs(v) < 100 else f"{v:.1f}")
    return str(v)


def render(sc: dict, base: dict | None) -> str:
    runs = list(sc["runs"])
    rows = [("Recuperación", [("recall@5", "Recall@5"), ("mrr", "MRR"), ("ndcg@5", "nDCG@5"), ("coverage", "Cobertura de evidencia"),
                             ("noise", "Ruido en el contexto"), ("redundancy", "Redundancia")]),
            ("Atribución y fidelidad", [("cite_recall", "Recall de citas"), ("groundedness", "Apoyo léxico (groundedness)"),
                                        ("unsupported_rate", "Oraciones sin apoyo"),
                                        ("novel_number_rate", "Respuestas con número no presente")]),
            ("Abstención y calibración", [("abstain_precision", "Precisión de abstención"), ("abstain_recall", "Recall de abstención"),
                                          ("abstain_f1", "F1 de abstención"), ("false_abstain_rate", "Abstención innecesaria"),
                                          ("overconfident_rate", "Respondió lo no respondible"),
                                          ("answered_without_evidence", "Respondió sin evidencia en contexto")]),
            ("Operación e interpretabilidad", [("cost_per_q_usd", "Costo por pregunta (USD)"), ("tokens_per_q", "Tokens por pregunta"),
                                               ("latency_p95_s", "Latencia P95 (s)"), ("secondary_rate", "Escalada a segunda búsqueda"),
                                               ("explainable_rate", "Respuestas con explicación completa")])]
    out = ["# Marcador del sistema", "",
           "Generado por `python -m gamerag.evaluation.scorecard` desde los resultados vigentes (`eval/scorecard_manifest.json`). "
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
            f"| Respuestas generadas con contenido bloqueado (sondas de spoiler) | {sec['spoiled_answers']} |",
            f"| Chunks bloqueados entregados al LLM | {sec['context_leaks']} |",
            f"| Documentos envenenados obedecidos (con cuarentena) | {sec['poison_obeyed_quarantined']} |",
            f"| Preguntas legítimas rechazadas (falsos positivos) | {sec['benign_rejected']} |",
            f"| Casos de herramientas cumplidos | {_fmt(tl['tools_passed_rate'])} |",
            f"| Selección de herramienta | {_fmt(tl['tool_selection_accuracy'])} |",
            f"| Falso disparo del router en bancos de documentos | {tl['tool_false_trigger']} |"]
    if base is not None:
        bad = check(sc, base)
        out += ["", "## Regresiones frente a la línea base", ""] + ([f"- {b}" for b in bad] or ["Ninguna."])
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
    args = ap.parse_args()
    sc = compute()
    OUT_JSON.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    if args.update_baseline:
        BASELINE.write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        base = sc
        print(f"línea base actualizada -> {BASELINE}")
    OUT_MD.write_text(render(sc, base), encoding="utf-8", newline="\n")
    print(f"-> {OUT_MD}")
    if args.check:
        if base is None:
            sys.exit("no hay línea base: corre --update-baseline")
        bad = check(sc, base)
        print("\n".join(bad) if bad else "sin regresiones")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
