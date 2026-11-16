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
    for key in ("generator", "retriever"):
        if g["run"].get(key) != b["run"].get(key):
            raise ValueError(f"Guarded y baseline no son comparables: {key} difiere")
    out = ["# Reporte de seguridad y pruebas adversarias", "",
           f"Corrida con controles: {g['run']['date']}. Renderizado por "
           "`python -m gamerag.evaluation.security_report`. Generador: "
           f"`{g['run']['generator']}`; recuperador: `{g['run']['retriever']}`. Datos: "
           "`eval/security_cases.jsonl`, `eval/security_spoilers.jsonl`, `eval/results/*_security_*.json`.", "",
           "**Guarded** = configuración declarada en el artefacto con guardrails de seguridad y política de acceso. "
           "**Baseline** = controles de inyección, PII, cuarentena y progreso desactivados; se conservan G1, "
           "el router y los controles por rol de la API. Una corrida extractiva no evalúa el comportamiento del perfil full "
           "con LLM. Las sondas históricas basadas en LocationGate miden coherencia de metadatos; no constituyen "
           "un oráculo independiente de seguridad del texto.", "",
           "Las cifras describen los artefactos de esa fecha; volver a renderizarlas no ejecuta el sistema ni "
           "evalúa cambios posteriores. Las verificaciones de la implementación vigente se distinguen en "
           "[controles](controls.md) y [auditoría](../evaluation/audit-current.md).", "",
           "## 1. Resumen", "",
           "| Vector | Casos | Guarded | Baseline |", "| --- | ---: | ---: | ---: |"]
    for key, (title, _) in VECTORS.items():
        gv, bv = g["by_vector"].get(key), b["by_vector"].get(key)
        if gv:
            out.append(f"| {title} | {gv['n']} | {_pct(gv['passed'], gv['n'])} | {_pct(bv['passed'], bv['n']) if bv else '-'} |")
    gs, bs = g["spoiler_probes"]["total"], b["spoiler_probes"]["total"]
    gp = {p["quarantine"]: p for p in g["poisoning"]}
    out += ["", f"- **Sondas de spoiler** ({gs['n']} preguntas por contenido aún bloqueado para `novato`, {len(g['spoiler_probes']['by_game'])} juegos): "
            f"contextos bloqueados entregados al generador **{gs['context_leak']}/{gs['n']}** "
            f"(baseline {bs['context_leak']}/{bs['n']}); "
            f"respuestas no abstentivas generadas con ese contexto **{gs['spoiled']}/{gs['n']}** "
            f"(baseline {bs['spoiled']}/{bs['n']}); "
            f"fugas textuales detectadas por la heurística histórica **{gs['answer_leak']}/{gs['n']}** "
            f"(baseline {bs['answer_leak']}/{bs['n']}).",
            f"- **Envenenamiento del corpus** (5 documentos con instrucciones, recuperador BM25): "
            f"canarios expuestos sin cuarentena **{gp[False]['obeyed']}/{gp[False]['n']}**, "
            f"con cuarentena **{gp[True]['obeyed']}/{gp[True]['n']}** "
            f"({gp[False]['retrieved'] - gp[True]['retrieved']} de {gp[False]['retrieved']} chunks envenenados retirados antes del generador).",
            f"- **Falsos positivos**: {g['benign_controls']['rejected']} de {g['benign_controls']['n']} preguntas legítimas "
            f"de los bancos de evaluación rechazadas; {g['benign_controls']['redacted']} redactadas.",
            f"- **Escaneo del corpus**: {g['corpus_scan']['flagged']} de {g['corpus_scan']['chunks']} chunks con firma fuerte "
            f"de inyección ({', '.join(c for c, _ in g['corpus_scan']['examples']) or 'ninguno'}). "
            "Este reporte no certifica revisión humana de las alertas.",
            f"- **Control por rol (API)**: {sum(r['passed'] for r in g['role_access'])}/{len(g['role_access'])} comprobaciones.", ""]
    inj = [c for c in b["cases"] if c["expect"] == "rejected_input"]
    eff = [c["id"] for c in inj if "effect_on_llm=True" in c["observed"]]
    out += ["## 2. Comportamiento observado", "",
            f"Sin guardrails de entrada, {len(eff)} de {len(inj)} ataques directos/bypass tuvieron efecto observable en la "
            f"respuesta del generador `{b['run']['generator']}` ({', '.join(eff) or 'ninguno'}). "
            "La presencia de un canario en una salida extractiva indica exposición del texto; no demuestra obediencia "
            "de un LLM. Los controles se interpretan dentro de la configuración registrada.", ""]
    if oracle := g.get("content_oracle"):
        out += ["## Oráculo independiente de contenido", "",
                f"Banco `eval/security_content_oracle_v2.jsonl`: {oracle['passed']}/{oracle['n']} casos cumplidos; "
                f"fugas en respuesta: {oracle['answer_leaks']}; fugas en evidencia final: {oracle['evidence_leaks']}; "
                f"fallos de disponibilidad: {oracle['availability_failures']}; errores: {oracle['errors']}.", "",
                "Las reglas del banco inspeccionan texto y perfiles fijados previamente, sin reutilizar la política "
                "de acceso. Se comprueba tanto ocultar contenido futuro como conservar contenido ya permitido.", ""]
    if quest := g.get("quest_oracle"):
        out += [f"Oráculo de quests (`eval/security_quest_oracle_v2.jsonl`): {quest['passed']}/{quest['n']}; "
                f"fugas en respuesta: {quest['answer_leaks']}; fugas en evidencia: {quest['evidence_leaks']}; "
                f"fallos de disponibilidad: {quest['availability_failures']}.", ""]

    out += ["## 3. Pruebas por vector (amenaza, componente, esperado, observado, mitigación)", ""]
    for key, (title, mitig) in VECTORS.items():
        cases = [c for c in g["cases"] if c["vector"] == key]
        if not cases:
            continue
        ok = sum(c["passed"] for c in cases)
        expected = "; ".join(f"`{value}`" for value in sorted({c["expect"] for c in cases}))
        out += [f"### {title}", "",
                f"**Amenaza:** {cases[0]['threat']}  ", f"**Componente afectado:** {cases[0]['component']}  ",
                f"**Comportamientos esperados según el caso:** {expected}  ",
                f"**Resultado observado:** {ok}/{len(cases)} cumplen (baseline: {b['by_vector'][key]['passed']}/{len(cases)})  ",
                f"**Mitigación implementada:** {mitig}", "",
                "| id | pregunta | esperado | cumple | observado |", "| --- | --- | --- | :-: | --- |"]
        for c in cases:
            q = c["question"].replace("|", "\\|").replace("\n", " ")[:70]
            out.append(f"| {c['id']} | {q} | `{c['expect']}` | {'sí' if c['passed'] else '**no**'} | "
                       f"{c['observed'].replace('|', '/')[:90]} |")
        out.append("")

    out += ["### Inyección indirecta (envenenamiento de fuentes)", "",
            "**Amenaza:** un documento del corpus contiene instrucciones dirigidas al modelo.  ",
            "**Componente afectado:** corpus + generador.  ",
            "**Comportamiento esperado:** retirar instrucciones de las fuentes y evitar exponer su canario.  ",
            f"**Resultado observado:** canarios expuestos sin cuarentena {gp[False]['obeyed']}/{gp[False]['n']}; "
            "con cuarentena "
            f"{gp[True]['obeyed']}/{gp[True]['n']}.  ",
            "**Mitigación implementada:** `QuarantineFilter` (firmas fuertes) + prompt del sistema (documentos = datos).", "",
            "| documento | recuperado | canario expuesto sin cuarentena | canario expuesto con cuarentena |",
            "| --- | :-: | :-: | :-: |"]
    for a, c in zip(gp[False]["rows"], gp[True]["rows"], strict=True):
        out.append(f"| {a['poison']} | {'sí' if a['retrieved'] else 'no'} | {'**sí**' if a['obeyed'] else 'no'} | "
                   f"{'**sí**' if c['obeyed'] else 'no'}{' (en contexto)' if c['retrieved'] else ' (en cuarentena)'} |")
    out += ["", "### Evasión de spoilers (sondas por juego)", "",
            "| juego | sondas | bloqueo duro | abstención | contexto bloqueado | respuestas con contexto bloqueado | "
            "fuga textual heurística |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for game, r in g["spoiler_probes"]["by_game"].items():
        out.append(f"| {game} | {r['n']} | {r['blocked']} | {r['abstained']} | {r['context_leak']} | "
                   f"{r['spoiled']} | {r['answer_leak']} |")
    out += ["", "En baseline (sin gates) el contenido bloqueado llega al generador en "
            f"{bs['context_leak']}/{bs['n']} sondas y {bs['spoiled']} respuestas se generan con él. "
            f"La heurística textual detecta {bs['answer_leak']}/{bs['n']}; ese valor no descarta exposición "
            "de información que el propio contexto de la heurística consideró permitida.", "",
            "### Control de acceso por rol", "", "| comprobación | observado | esperado | cumple |", "| --- | --- | --- | :-: |"]
    for r in g["role_access"]:
        out.append(f"| {r['check']} | {r['observed']} | {r['expected']} | {'sí' if r['passed'] else '**no**'} |")

    out += ["", "## 4. Limitaciones conocidas", "",
            "- Las heurísticas de inyección se basan en firmas; una instrucción con otra formulación puede pasar "
            "el control. El comportamiento del generador se informa por caso sin atribuir resultados extractivos "
            "a la resistencia de un LLM.",
            "- La cuarentena de chunks usa firmas fuertes; la tabla anterior registra qué documentos se recuperaron "
            "y expusieron el canario. Una prueba extractiva no permite atribuir resistencia a un modelo generativo.",
            "- La fuga de spoilers en la respuesta se mide con una heurística de términos distintivos y por el contexto "
            "entregado en la sonda histórica. El oráculo independiente usa patrones de contenido fijados en el banco; "
            "no detecta todas las paráfrasis posibles ni certifica ausencia universal de spoilers.",
            "- El detector no cubre ataques multiturno (el sistema es de un solo turno) ni ofuscación (base64, leetspeak).",
            "- Los límites de herramientas (máximo de llamadas, timeouts) se documentan en `docs/tools/README.md`.", ""]
    return "\n".join(line.rstrip() + ("<br>" if line.endswith("  ") else "") for line in out)


def main() -> None:
    text = render(_latest("guarded"), _latest("baseline"))
    path = Path("docs/security/report.md")
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"-> {path} ({len(text.splitlines())} líneas)")


if __name__ == "__main__":
    main()
