"""Evaluación de herramientas y orquestación (§5.6 y §8): selección, ejecución, parámetros, confirmación, degradación.

    uv run python -m gamerag.evaluation.tools_eval            # offline: BM25 + generador extractivo, sin costo

Casos de `eval/cases_tools.jsonl` (esquema del §8 más `expect`). Categorías:

- `nominal`: la herramienta correcta se elige y se ejecuta con citas/sin spoilers.
- `wrong_tool`: preguntas que parecen de herramienta pero deben ir a documentos (selección errónea).
- `out_of_range`: parámetros fuera de rango; no se ejecuta, se explica.
- `confirmation`: acciones que cambian el perfil; nunca se ejecutan, exigen revisión humana.
- `degradation`: la herramienta falla o excede el tiempo (`fault`); se degrada al RAG y se responde igual.

Además mide la **tasa de falso disparo**: preguntas legítimas de los bancos de documentos que el router desvía a una
herramienta (debe ser 0).
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

from gamerag.games import load_all_games
from gamerag.pipeline import Pipeline, build_pipeline
from gamerag.progress.models import load_profiles
from gamerag.settings import Settings, get_settings

CASES = "eval/cases_tools.jsonl"
DOC_BANKS = ["eval/cases.jsonl", "eval/cases_hard.jsonl", "eval/synthetic_train.jsonl"]


def _fault(pipe: Pipeline, kind: str | None):
    """Inyecta una falla en la ejecución de herramientas; devuelve la función que la deshace."""
    if not kind:
        return lambda: None
    orig = pipe.router.run

    def broken(*a, **k):
        if kind == "raise":
            raise RuntimeError("tool backend unavailable")
        time.sleep(pipe.tool_timeout_s * 4)  # "timeout": excede el límite configurado
    pipe.router.run = broken
    return lambda: setattr(pipe.router, "run", orig)


def _check(case: dict, ans, trace) -> tuple[bool, str]:
    exp = case["expect"]
    obs = {"route": trace.route, "tool_used": ans.tool_used, "abstained": ans.abstained,
           "needs_human_review": ans.needs_human_review, "status": (trace.tool or {}).get("status"),
           "executed": (trace.tool or {}).get("executed"), "sources": len(ans.sources),
           "blocked_rows": (trace.tool or {}).get("blocked_rows"), "outcome": trace.outcome}
    ok = True
    for key, want in exp.items():
        if key == "min_sources":
            ok &= obs["sources"] >= want
        elif key == "min_blocked_rows":
            ok &= (obs["blocked_rows"] or 0) >= want
        elif key == "answered":  # respondió (sin abstenerse) con contexto, incluso tras degradar
            ok &= (not ans.abstained) == want
        else:
            ok &= obs.get(key) == want
    return ok, json.dumps({k: v for k, v in obs.items() if v not in (None, False) or k in exp}, ensure_ascii=False)


def run(cases_path: str = CASES) -> dict:
    base = get_settings()
    s = Settings(root=base.root, retriever="bm25", generator="extractive", router=True, tool_timeout_s=0.3)
    pipe = build_pipeline(s)
    games = load_all_games(s.path(s.games_config_dir))
    profiles = load_profiles(s.path(s.seed_profiles), games)
    cases = [json.loads(x) for x in Path(cases_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    rows, by_cat, tool_ms = [], defaultdict(list), []
    for c in cases:
        undo = _fault(pipe, c.get("fault"))
        try:
            ans, trace = pipe.ask(c["question"], c["game"], profiles[c["profile"]])
            ok, observed = _check(c, ans, trace)
            if trace.latency_ms.get("tool") and not c.get("fault"):
                tool_ms.append(trace.latency_ms["tool"])
        except Exception as exc:  # noqa: BLE001
            ok, observed = False, f"error: {type(exc).__name__}: {exc}"
        finally:
            undo()
        by_cat[c["category"]].append(ok)
        rows.append({"id": c["id"], "category": c["category"], "question": c["question"], "passed": ok,
                     "expected": c["expect"], "observed": observed})
    # falso disparo: preguntas de documentos desviadas a una herramienta
    routed = []
    total = 0
    for f in DOC_BANKS:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("game") not in pipe.router.games:
                continue
            total += 1
            if pipe.router.route(d["question"], d["game"]).is_tool:
                routed.append((d["id"], d["question"][:70]))
    sel = [r for r in rows if r["category"] in ("nominal", "wrong_tool")]
    return {
        "run": {"date": date.today().isoformat(), "retriever": "bm25", "generator": "extractive"},
        "by_category": {k: {"passed": sum(v), "n": len(v)} for k, v in by_cat.items()},
        "tool_selection_accuracy": round(mean(r["passed"] for r in sel), 4) if sel else None,
        "overall": round(mean(r["passed"] for r in rows), 4),
        "tool_latency_ms_mean": round(mean(tool_ms), 2) if tool_ms else None,
        "false_trigger": {"n": total, "routed_to_tool": len(routed), "examples": routed[:8]},
        "cases": rows,
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=CASES, help="banco de casos (por defecto eval/cases_tools.jsonl)")
    args = ap.parse_args()
    res = run(args.cases)
    tag = "tools" if args.cases == CASES else "tools_" + Path(args.cases).stem.split("_")[-1]
    out = Path("eval/results") / f"{date.today().isoformat()}_{tag}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: res[k] for k in ("by_category", "tool_selection_accuracy", "overall",
                                           "tool_latency_ms_mean", "false_trigger")}, ensure_ascii=False, indent=1))
    for r in res["cases"]:
        if not r["passed"]:
            print("FALLA", r["id"], r["question"][:60], "|", r["observed"][:140])
    print(f"-> {out}")


if __name__ == "__main__":
    main()
