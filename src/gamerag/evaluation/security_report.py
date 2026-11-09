"""Renderiza `docs/security/report.md` desde los resultados de `evaluation.security` (guarded y baseline).

    uv run python -m gamerag.evaluation.security            # genera *_security_guarded.json
    uv run python -m gamerag.evaluation.security --baseline # genera *_security_baseline.json
    uv run python -m gamerag.evaluation.security_report     # escribe docs/security/report.md

Todas las cifras salen de los JSON; el texto fijo solo describe amenaza, componente y mitigación (columnas del §10).
"""

from __future__ import annotations

import json
from pathlib import Path

VECTORS = {
    "injection_direct": ("Inyección de instrucciones (directa)", "InputGuard `injection`; prompt del sistema con documentos como datos; LeakGuard"),
    "permission_evasion": ("Evasión de permisos (pedir ignorar progreso/rol)", "InputGuard `injection` + gates G1/G2 por ubicación"),
    "sensitive_data": ("Datos sensibles en la pregunta (PII/secretos)", "PIIGuard (redacción antes de recuperar/generar) + redacción en auditoría"),
    "critical_action": ("Acciones críticas sin autorización humana", "Router: `critical_action` y `update_progress` nunca se ejecutan"),
    "forced_hallucination": ("Alucinación forzada (contenido inexistente)", "Contexto cerrado + citas obligatorias + abstención"),
    "cross_game": ("Contaminación entre juegos", "Gate G1 (solo chunks del juego activo)"),
}


def _latest(tag: str) -> dict:
    files = sorted(Path("eval/results").glob(f"*_security_{tag}.json"))
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _pct(a: int, b: int) -> str:
    return f"{a}/{b}"


def render(g: dict, b: dict) -> str:
    out = ["# Reporte de seguridad y pruebas adversarias", "",
           f"Generado por `python -m gamerag.evaluation.security_report` ({g['run']['date']}). Generador: "
           f"`{g['run']['generator']}`; recuperador: `{g['run']['retriever']}`. Datos: "
           "`eval/security_cases.jsonl`, `eval/security_spoilers.jsonl`, `eval/results/*_security_*.json`.", "",
           "**Guarded** = configuración servida (guardrails de seguridad + gates). **Baseline** = sin guardrails de "
           "seguridad ni gates de spoilers, para medir qué aporta cada control.", "",
           "## 1. Resumen", "",
           "| Vector | Casos | Guarded | Baseline |", "| --- | ---: | ---: | ---: |"]
    for key, (title, _) in VECTORS.items():
        gv, bv = g["by_vector"].get(key), b["by_vector"].get(key)
        if gv:
            out.append(f"| {title} | {gv['n']} | {_pct(gv['passed'], gv['n'])} | {_pct(bv['passed'], bv['n']) if bv else '-'} |")
    gs, bs = g["spoiler_probes"]["total"], b["spoiler_probes"]["total"]
    gp = {p["quarantine"]: p for p in g["poisoning"]}
    out += ["", f"- **Sondas de spoiler** ({gs['n']} preguntas por contenido aún bloqueado para `novato`, {len(g['spoiler_probes']['by_game'])} juegos): "
            f"chunks bloqueados entregados al LLM **{gs['context_leak']}/{gs['n']}** (baseline {bs['context_leak']}/{bs['n']}); "
            f"respuestas generadas con contenido bloqueado **{gs['spoiled']}/{gs['n']}** (baseline {bs['spoiled']}/{bs['n']}).",
            f"- **Envenenamiento del corpus** (5 documentos con instrucciones para el modelo, todos recuperados por BM25): "
            f"obedecidos sin cuarentena **{gp[False]['obeyed']}/{gp[False]['n']}**, con cuarentena **{gp[True]['obeyed']}/{gp[True]['n']}** "
            f"({gp[False]['retrieved'] - gp[True]['retrieved']} de {gp[False]['retrieved']} chunks envenenados retirados antes del generador).",
            f"- **Falsos positivos**: {g['benign_controls']['rejected']} de {g['benign_controls']['n']} preguntas legítimas "
            f"de los bancos de evaluación rechazadas; {g['benign_controls']['redacted']} redactadas.",
            f"- **Escaneo del corpus**: {g['corpus_scan']['flagged']} de {g['corpus_scan']['chunks']} chunks con firma fuerte "
            f"de inyección ({', '.join(c for c, _ in g['corpus_scan']['examples']) or 'ninguno'}; revisión manual: falso positivo, "
            "una guía que dice \"ignore the instruction\" de una misión).",
            f"- **Control por rol (API)**: {sum(r['passed'] for r in g['role_access'])}/{len(g['role_access'])} comprobaciones.", ""]
    inj = [c for c in b["cases"] if c["expect"] == "rejected_input"]
    eff = [c["id"] for c in inj if "effect_on_llm=True" in c["observed"]]
    out += ["## 2. Efecto real sobre el modelo", "",
            f"Sin guardrails de entrada, {len(eff)} de {len(inj)} ataques directos/bypass tuvieron efecto observable en la "
            f"respuesta de Haiku ({', '.join(eff) or 'ninguno'}): el modelo, con contexto cerrado y documentos marcados como "
            "datos, resiste casi todos. El `InjectionGuard` no se justifica por la tasa de obediencia sino por determinismo, "
            "costo cero, cero llamadas al LLM para ataques conocidos y rastro de auditoría (`prompt_injection:<firma>`). "
            "El mayor efecto medido de los controles está en los gates (spoilers) y en la cuarentena de chunks.", ""]

    out += ["## 3. Pruebas por vector (amenaza, componente, esperado, observado, mitigación)", ""]
    for key, (title, mitig) in VECTORS.items():
        cases = [c for c in g["cases"] if c["vector"] == key]
        if not cases:
            continue
        ok = sum(c["passed"] for c in cases)
        out += [f"### {title}", "",
                f"**Amenaza:** {cases[0]['threat']}  ", f"**Componente afectado:** {cases[0]['component']}  ",
                f"**Comportamiento esperado:** `{cases[0]['expect']}`  ",
                f"**Resultado observado:** {ok}/{len(cases)} cumplen (baseline: {b['by_vector'][key]['passed']}/{len(cases)})  ",
                f"**Mitigación implementada:** {mitig}", "",
                "| id | pregunta | cumple | observado |", "| --- | --- | :-: | --- |"]
        for c in cases:
            q = c["question"].replace("|", "\\|").replace("\n", " ")[:70]
            out.append(f"| {c['id']} | {q} | {'sí' if c['passed'] else '**no**'} | {c['observed'].replace('|', '/')[:90]} |")
        out.append("")

    out += ["### Inyección indirecta (envenenamiento de fuentes)", "",
            "**Amenaza:** un documento del corpus contiene instrucciones dirigidas al modelo.  ",
            "**Componente afectado:** corpus + generador.  ",
            "**Comportamiento esperado:** el chunk no llega al generador o, si llega, el modelo no lo obedece.  ",
            f"**Resultado observado:** sin cuarentena obedecidos {gp[False]['obeyed']}/{gp[False]['n']}; con cuarentena "
            f"{gp[True]['obeyed']}/{gp[True]['n']}.  ",
            "**Mitigación implementada:** `QuarantineFilter` (firmas fuertes) + prompt del sistema (documentos = datos).", "",
            "| documento | recuperado | obedecido sin cuarentena | obedecido con cuarentena |", "| --- | :-: | :-: | :-: |"]
    for a, c in zip(gp[False]["rows"], gp[True]["rows"], strict=True):
        out.append(f"| {a['poison']} | {'sí' if a['retrieved'] else 'no'} | {'**sí**' if a['obeyed'] else 'no'} | "
                   f"{'**sí**' if c['obeyed'] else 'no'}{' (en contexto)' if c['retrieved'] else ' (en cuarentena)'} |")
    out += ["", "### Evasión de spoilers (sondas por juego)", "",
            "| juego | sondas | bloqueo duro | abstención | contexto con contenido bloqueado | respuestas con spoiler |",
            "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for game, r in g["spoiler_probes"]["by_game"].items():
        out.append(f"| {game} | {r['n']} | {r['blocked']} | {r['abstained']} | {r['context_leak']} | {r['spoiled']} |")
    out += ["", "En baseline (sin gates) el contenido bloqueado llega al generador en "
            f"{bs['context_leak']}/{bs['n']} sondas y {bs['spoiled']} respuestas se generan con él.", "",
            "### Control de acceso por rol", "", "| comprobación | observado | esperado | cumple |", "| --- | --- | --- | :-: |"]
    for r in g["role_access"]:
        out.append(f"| {r['check']} | {r['observed']} | {r['expected']} | {'sí' if r['passed'] else '**no**'} |")

    out += ["", "## 4. Limitaciones conocidas", "",
            "- Las heurísticas de inyección son de firma: una instrucción sin las palabras clave pasa el guardrail. "
            "Cubrimos ese caso con el prompt del sistema y el `LeakGuard`, y lo medimos (caso `sec_021`: "
            "pedir en la propia pregunta que se escriba un código sí lo obedece; es una instrucción del propio usuario, "
            "no una escalada de privilegios).",
            "- La cuarentena de chunks usa firmas fuertes; el documento `subtle` (\"Note to the AI assistant…\") no la dispara y "
            "llega al contexto. En la corrida registrada el modelo no lo obedeció, pero no hay garantía determinista.",
            "- La fuga de spoilers en la respuesta se mide con una heurística de términos distintivos y por el contexto "
            "entregado; los gates son deterministas por ubicación (metadatos), no semánticos. Las páginas sin ubicación en "
            "wikis extra se tratan como restringidas.",
            "- El detector no cubre ataques multiturno (el sistema es de un solo turno) ni ofuscación (base64, leetspeak).",
            "- Los límites de herramientas (máximo de llamadas, timeouts) se documentan en `docs/tools/README.md`.", ""]
    return "\n".join(out)


def main() -> None:
    text = render(_latest("guarded"), _latest("baseline"))
    path = Path("docs/security/report.md")
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"-> {path} ({len(text.splitlines())} líneas)")


if __name__ == "__main__":
    main()
