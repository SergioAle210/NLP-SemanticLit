"""Componentes del sistema de diseño "Puesto de Control" como funciones que devuelven HTML.

Todo texto que viene de la API, del modelo o del usuario pasa por `html.escape`: la respuesta de un LLM y el
corpus no son confiables, y estas cadenas se inyectan como HTML. Las funciones son puras (sin Gradio ni red) para
poder probarlas.
"""

from __future__ import annotations

from html import escape
from urllib.parse import urlsplit

# Glifos de píxel del sistema de diseño (ver puesto.css: .pc-px--<nombre>)
VERDICTS = {
    "ok": ("ok", "Aprobado", "check"),
    "warn": ("warn", "Sin evidencia", "dots"),
    "blocked": ("deny", "Bloqueado", "cross"),
    "rejected": ("deny", "Rechazado", "cross"),
    "review": ("review", "Revisión humana", "eye"),
    "quarantine": ("quarantine", "En cuarentena", "diamond"),
}


def e(x) -> str:
    return escape("" if x is None else str(x), quote=True)


def technical_detail(value) -> str:
    return ('<details class="pc-technical"><summary>Ver detalle técnico</summary>'
            f'<pre>{e(value)}</pre></details>')


def rejection_message(detail) -> str:
    if "prompt_injection" in str(detail):
        return "La consulta intenta cambiar las reglas del asistente o revelar instrucciones internas. Reformula tu pregunta sobre el juego."
    return "La consulta no pasó los controles de entrada. Revisa el texto e inténtalo de nuevo."


def px(name: str, extra: str = "") -> str:
    return f'<span class="pc-px pc-px--{e(name)}{extra}" aria-hidden="true"></span>'


def stamp(kind: str, small: bool = False, hit: bool = False) -> str:
    variant, word, icon = VERDICTS[kind]
    cls = ("" if variant == "ok" else f" pc-stamp--{variant}") + (" pc-stamp--sm" if small else "") + \
          (" pc-stamp--hit" if hit else "")
    return f'<span class="pc-stamp{cls}">{px(icon)}{e(word)}</span>'


def redact(chars: int = 9, label: str = "contenido retenido") -> str:
    return f'<span class="pc-redact" role="img" aria-label="{e(label)}" style="width:{int(chars)}ch">&nbsp;</span>'


def verdict(answer: dict, trace: dict) -> str:
    """Veredicto del expediente según la respuesta y la traza (prioridad: rechazo > bloqueo > revisión > abstención)."""
    outcome = trace.get("outcome")
    if outcome == "rejected_input":
        return "rejected"
    tool = trace.get("tool") or {}
    if outcome == "blocked_by_access" or answer.get("blocked_by_spoiler") or (
            tool.get("blocked_rows") and not tool.get("rows")):  # la herramienta ocultó todas las filas por progreso
        return "blocked"
    if answer.get("needs_human_review"):
        return "review"
    if answer.get("abstained"):
        return "warn"
    return "ok"


def blocked_count(trace: dict) -> int:
    return sum(1 for c in trace.get("candidates", []) if c.get("blocked_by")) + int(
        (trace.get("tool") or {}).get("blocked_rows") or 0)


def reference(n: int, source: dict, hit: dict | None = None, active: bool = False) -> str:
    """Referencia numerada; si hay fragmento, se abre con <details> (sin JavaScript)."""
    label = e(source.get("source", ""))
    cid = e(source.get("chunk_id", ""))
    # ids de las wikis extra: "juego:sitio:pagina:n" (cuatro partes); los de StrategyWiki: "juego:pagina:n"
    extra = source.get("chunk_id", "").count(":") >= 3
    cls = "pc-ref" + (" pc-ref--active" if active else "") + (" pc-ref--extra" if extra else "")
    tag = (f'<span class="pc-ref__n">{n}</span><span class="pc-ref__t">{label}'
           f'<small>{cid}</small></span>')
    if not hit:
        return f'<span class="{cls}">{tag}</span>'
    url = hit.get("url")
    try:
        parsed = urlsplit(url or "")
        url = url if parsed.scheme in ("http", "https") and parsed.netloc else None
    except ValueError:
        url = None
    link = f' · <a href="{e(url)}" target="_blank" rel="noopener noreferrer">fuente</a>' if url else ""
    detail = f' · sección {e(source.get("page"))}'
    if hit.get("version"):
        detail += f' · {e(hit["version"])}'
    if hit.get("is_excerpt"):
        detail += ' · extracto autorizado'
    return (f'<details class="pc-refd"><summary class="{cls}" tabindex="0">{tag}</summary>'
            f'<div class="pc-excerpt"><div class="pc-label">Fragmento citado · {n}{detail}{link}</div>'
            f'{e(hit.get("text", ""))}</div></details>')


def dossier(question: str, game_title: str, profile_id: str, answer: dict, trace: dict,
            hits: list[dict] | None = None) -> str:
    kind = verdict(answer, trace)
    hits_by_id = {h.get("chunk_id"): h for h in hits or []}
    sources = answer.get("sources", [])
    cites = "".join(f'<span class="pc-cite" aria-label="referencia {i}">{i}</span>' for i, _ in enumerate(sources, 1))
    body = e(answer.get("answer", ""))
    note = ""
    held = blocked_count(trace)
    if kind == "blocked":
        note = (f'<div class="pc-note">{px("cross")}<span class="pc-sm"><b>{held} fragmentos retenidos.</b> '
                'Pertenecen a contenido que aún no has desbloqueado.</span></div>') if held else (
            f'<div class="pc-note">{px("cross")}<span class="pc-sm">Contenido que aún no has desbloqueado.</span></div>')
    elif kind == "warn":
        ev = trace.get("evidence") or []
        why = ev[-1].get("reason") if ev else ""
        extra = f" Motivo del evaluador: {e(why)}." if why else ""
        note = f'<div class="pc-note">{px("dots")}<span class="pc-sm">No hay evidencia suficiente en el archivo.{extra}</span></div>'
    elif kind == "review":
        text = ("Solicitud detenida para revisión; esta interfaz no modifica el progreso."
                if answer.get("tool_used") in ("update_progress", "critical_action")
                else "Respuesta degradada o pendiente de revisión humana.")
        note = f'<div class="pc-note">{px("eye")}<span class="pc-sm">{text}</span></div>'
    elif kind == "rejected":
        guards = {k: v for k, v in (trace.get("input_guards") or {}).items() if v != "ok"}
        note = (f'<div class="pc-note">{px("cross")}<div class="pc-sm">Entrada rechazada: '
                f'{e(rejection_message(guards))}{technical_detail(guards)}</div></div>')
    refs = "".join(reference(i, s, hits_by_id.get(s.get("chunk_id")), active=(i == 1))
                   for i, s in enumerate(sources, 1))
    lat = round(sum((trace.get("latency_ms") or {}).values()))
    foot = f'<span>Referencias: {len(sources)}</span><span>Tiempo registrado: {lat} ms</span>'
    if trace.get("secondary"):
        foot += f'<span>Fragmentos adicionales consultados: {len(trace["secondary"])}</span>'
    return (
        '<article class="pc-paper pc-doss">'
        f'<div class="pc-doss__tab"><span>Expediente {e(str(trace.get("trace_id", ""))[:4].upper())}</span>'
        f'<span>{e(game_title)} · {e(profile_id)}</span></div>'
        f'<div class="pc-doss__q"><div class="pc-label">Consulta</div>{e(question)}</div>'
        f'<div class="pc-doss__a"><div class="pc-doss__stamp">{stamp(kind, hit=True)}</div>'
        f'<div class="pc-label">Respuesta</div>{body} {cites}{note}</div>'
        + (f'<div class="pc-doss__refs">{refs}</div>' if refs else "")
        + f'<div class="pc-doss__foot">{foot}</div></article>')


def rulebook(explanation: dict | None) -> str:
    if not explanation:
        return ""
    items = []
    rejected = next((s for s in explanation.get("steps", [])
                     if s.get("stage") == "entrada" and not s.get("ok")), None)

    def li(cls: str, icon: str, title: str, text: str) -> None:
        items.append(f'<li><span class="{cls}">{px(icon)}</span><div><b>{e(title)}</b><br>{text}</div></li>')

    n = 0
    for step in explanation.get("steps", []):
        stage = step.get("stage", "")
        if rejected is not None and stage != "entrada":
            continue  # No presentar etapas no ejecutadas como comprobaciones superadas.
        n += 1
        title = f"{n} {stage.capitalize()}"
        if stage == "entrada":
            if step.get("ok"):
                flags = ", ".join(step.get("flags") or [])
                li("pc-ok", "check", title, "Validaciones superadas." + (f" Señales: {e(flags)}." if flags else ""))
            else:
                li("pc-no", "cross", title, e(rejection_message(step.get("detail")))
                   + technical_detail(step.get("detail")))
        elif stage == "ruta":
            label = "Consulta de guías." if step.get("route") == "documents" else "Consulta mediante una herramienta."
            li("pc-ok", "check", title, label + technical_detail(f'{step.get("route")}: {step.get("why")}'))
        elif stage == "herramienta":
            ok = step.get("status") == "ok"
            li("pc-ok" if ok else "pc-wn", "check" if ok else "dots", title,
               f'{e(step.get("name"))}: {e(step.get("status"))}')
        elif stage == "recuperación":
            li("pc-ok", "check", title, f'{e(step.get("candidatos"))} candidatos; '
               f'{e(step.get("entregados_al_generador"))} entregados al generador.')
            held = step.get("bloqueados") or {}
            if held:
                n += 1
                total = sum(held.values())
                why = "; ".join(f"{e(k)} ({e(v)})" for k, v in held.items())
                li("pc-no", "cross", f"{n} Control de acceso", f"{total} fragmentos retenidos: {why} {redact(6)}")
        elif stage.startswith("evaluación"):
            ok = step.get("suficiente")
            li("pc-ok" if ok else "pc-wn", "check" if ok else "dots", title,
               "Evidencia suficiente." if ok else f'Insuficiente: {e(step.get("motivo"))}')
        elif stage == "segunda búsqueda":
            li("pc-wn", "dots", title, f'{e(step.get("chunks_de_otras_wikis"))} fragmentos de otras wikis.')
        elif stage == "salida":
            bad = {k: v for k, v in (step.get("guards") or {}).items() if v != "ok"}
            if bad:
                li("pc-no", "cross", title, "Rechazada: " + e("; ".join(bad.values())))
            else:
                li("pc-ok", "check", title, f'Citas verificadas ({len(step.get("citas") or [])}).')
    summary = ("La consulta se detuvo antes de buscar información o generar una respuesta."
               if rejected is not None else explanation.get("summary", ""))
    return ('<aside class="pc-paper pc-rules"><div class="pc-label">Reglamento de inspección</div>'
            f'<ol>{"".join(items)}</ol><p class="pc-sm pc-muted">{e(summary)}</p></aside>')


def telegram(trace: dict | None) -> str:
    if not trace:
        return ('<section class="pc-telegram" aria-label="Estado de la consulta">'
                '<strong>Listo para consultar</strong><p>Elige un juego y un perfil, escribe tu pregunta '
                'y pulsa Entregar.</p></section>')
    lat = round(sum((trace.get("latency_ms") or {}).values()), 1)
    outcome = trace.get("outcome", "")
    status, help_text = {
        "answered": ("Respuesta disponible", "Puedes abrir las referencias para consultar la evidencia utilizada."),
        "retrieved": ("Búsqueda completada", "Se muestran los fragmentos encontrados; no se generó una respuesta."),
        "abstained": ("Sin evidencia suficiente", "Prueba una pregunta más concreta sobre el juego seleccionado."),
        "rejected_input": ("Consulta rechazada", "Reformula la pregunta. Los controles de entrada impidieron continuar."),
        "blocked_by_access": ("Contenido protegido", "La información no está disponible para el progreso de este perfil."),
        "rejected_output": ("Respuesta retenida", "La respuesta no superó la validación y necesita revisión."),
    }.get(outcome, ("Consulta finalizada", "Consulta el resultado y las comprobaciones del panel."))
    if outcome not in ("rejected_input", "blocked_by_access", "rejected_output") and (
            trace.get("final_answer") or {}).get("needs_human_review"):
        status, help_text = "Revisión necesaria", "Consulta el aviso de la respuesta antes de utilizarla."
    parts = [("Identificador de consulta", trace.get("trace_id", "")), ("Ruta interna", trace.get("route", "")),
             ("Generador configurado", trace.get("generator", "")),
             ("Método de recuperación", trace.get("retriever", "")), ("Código de resultado", outcome)]
    details = "".join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in parts)
    return ('<section class="pc-telegram" aria-label="Estado de la consulta">'
            f'<div class="pc-status-line"><strong>{e(status)}</strong><span>Tiempo registrado: {lat} ms</span></div>'
            f'<p>{e(help_text)}</p><details class="pc-technical"><summary>Ver detalles técnicos</summary>'
            f'<dl>{details}</dl></details></section>')


def bar(done: int, now: int | None, total: int, label: str) -> str:
    cells = "".join('<i class="on"></i>' if i < done else ('<i class="now"></i>' if i == now else "<i></i>")
                    for i in range(total))
    return f'<span class="pc-bar" role="img" aria-label="{e(label)}">{cells}</span>'


def passport(profile: dict, games: list[dict]) -> str:
    by_id = {g["game_id"]: g for g in games}
    role = profile.get("role", "player")
    tags = f'<span class="pc-tag">{e(role)}</span>'
    rows = []
    if role in ("completionist", "admin"):
        rows.append('<div class="pc-sm pc-muted">Rol sin restricciones de spoilers: el visado cubre todos los niveles.</div>')
    else:
        for gid, prog in (profile.get("progress") or {}).items():
            g = by_id.get(gid)
            if not g or not g.get("available"):
                continue
            if prog.get("kind") == "level_set":
                levels = g.get("levels") or list(range(1, 10))
                done = len(prog.get("completed_levels") or [])
                cur = prog.get("current_level")
                label = f"{done} de {len(levels)} completados; nivel {cur} en curso"
                rows.append(f'<div class="pc-visa"><span class="pc-visa__name">{e(g["title"])}</span>'
                            f'{bar(done, (done if cur else None), len(levels), label)}'
                            f'<span class="pc-sm pc-muted">Quest {e(prog.get("quest"))} · nivel {e(cur)}</span><span></span></div>')
            elif prog.get("kind") == "linear_stage":
                rows.append(f'<div class="pc-visa"><span class="pc-visa__name">{e(g["title"])}</span><span></span>'
                            f'<span class="pc-sm pc-muted">Etapa {e(prog.get("current_stage"))}</span><span></span></div>')
    return ('<section class="pc-paper pc-pass" style="width:100%"><div class="pc-pass__head"><div class="pc-pass__seal">'
            f'{px("seal", " pc-px--lg")}</div><div><div class="pc-label" style="color:var(--paper)">Pasaporte del jugador</div>'
            f'<h3 class="pc-title">{e(profile.get("user_id"))}</h3></div></div>'
            f'<div class="pc-pass__body"><div class="pc-row" style="gap:var(--space-2)">{tags}</div>'
            f'<div class="pc-col" style="gap:var(--space-3)">{"".join(rows)}</div>'
            '<div class="pc-sm pc-muted">Lo que está fuera de su visado no se entrega.</div></div></section>')


# --- informe del turno ------------------------------------------------------------------------------------

REPORT_ROWS = [  # Las metas proceden del artefacto, no de umbrales distintos en la interfaz.
    ("recall@5", "Acierto de recuperación en top-5", "{:.3f}"),
    ("cite_precision", "Precisión de citas (relevancia)", "{:.3f}"),
    ("coverage", "Cobertura de evidencia", "{:.3f}"),
    ("groundedness", "Apoyo léxico de la respuesta", "{:.3f}"),
    ("noise", "Ruido en el contexto", "{:.3f}"),
    ("abstention_accuracy", "Exactitud global de abstención", "{:.3f}"),
    ("abstain_recall", "Recall de abstención", "{:.3f}"),
    ("abstain_f1", "F1 de abstención", "{:.3f}"),
    ("latency_p95_s", "Latencia P95 (s)", "{:.3f}"),
]


def report(scorecard: dict | None, run: str = "principal") -> str:
    if not scorecard or run not in scorecard.get("runs", {}):
        return ('<section class="pc-paper pc-report"><div class="pc-label">Informe del turno</div>'
                '<p>No hay marcador disponible. Genéralo con <code>python -m gamerag.evaluation.scorecard</code>.</p></section>')
    m = scorecard["runs"][run]
    sec, tl = scorecard.get("security", {}), scorecard.get("tools", {})
    targets = scorecard.get("targets", {}).get(run, {})
    rows = []
    for key, label, fmt in REPORT_ROWS:
        v = m.get(key)
        if v is None:
            continue
        status = targets.get(key, {}).get("status")
        badge = (stamp("ok", True) if status == "met" else _warn_stamp() if status == "unmet"
                 else '<span class="pc-muted">Sin meta evaluable</span>')
        rows.append(f'<tr><td>{e(label)}</td><td class="n">{fmt.format(v)}</td>'
                    f'<td class="st">{badge}</td></tr>')
    for label, val in (("Respuestas con spoiler (sondas)", sec.get("spoiled_answers")),
                       ("Falso disparo del router", tl.get("tool_false_trigger"))):
        if val is not None:
            rows.append(f'<tr><td>{e(label)}</td><td class="n">{e(val)}</td>'
                        f'<td class="st">{stamp("ok", True) if val == 0 else _warn_stamp()}</td></tr>')
    big = "".join(f'<div><div class="pc-bignum">{e(v)}</div><div class="pc-label">{e(k)}</div></div>' for k, v in (
        ("Acierto top-5", f'{m.get("recall@5", 0):.3f}'),
        ("Spoilers", f'{sec.get("spoiled_answers", "?")}'),
        ("Seguridad", f'{sec.get("security_passed_rate", 0):.2f}')))
    provenance = m.get("provenance", {})
    origin = " · ".join(str(provenance.get(key) or "no registrado") for key in ("date", "generator", "retriever"))
    historical = provenance.get("schema_version", 1) < 2
    note = "Corrida histórica; no mide el servicio abierto ahora." if historical else "Corrida registrada; consulte su configuración efectiva."
    return ('<section class="pc-paper pc-report"><div class="pc-label">Informe del turno</div>'
            f'<h3 class="pc-title" style="font-size:22px;line-height:24px;margin-bottom:var(--space-3)">Banco {e(run)} · {e(m.get("n"))} casos</h3>'
            f'<div class="pc-row" style="gap:var(--space-6);margin-bottom:var(--space-4)">{big}</div>'
            f'<p class="pc-sm">{e(note)} {e(origin)}</p>'
            '<table><thead><tr><th>Métrica</th><th class="n">Valor</th><th class="st">Meta</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></section>')


def _warn_stamp() -> str:
    return stamp("warn", True).replace("Sin evidencia", "Revisar")


def audit_table(rows: list[dict]) -> str:
    if not rows:
        return '<p class="pc-sm">El archivo está vacío.</p>'
    head = ("fecha", "usuario", "juego", "pregunta", "resultado", "contexto", "bloqueados", "ms")
    body = "".join("<tr>" + "".join(f"<td>{e(r.get(k))}</td>" for k in head) + "</tr>" for r in rows)
    return ('<div class="pc-paper pc-report" style="width:100%;overflow-x:auto"><table><thead><tr>'
            + "".join(f"<th>{e(k)}</th>" for k in head) + f"</tr></thead><tbody>{body}</tbody></table></div>")


def topbar(health: dict | None) -> str:
    state = "Servicio conectado" if health else "Servicio no disponible"
    modes = {"extractive": "Respuestas con extractos de las guías",
             "haiku": "Respuestas redactadas con IA",
             "haiku+fallback": "Modo IA con respaldo de las guías"}
    mode = modes.get(health.get("generator"), "Consulta de guías disponible") if health else ""
    extra = f" · {e(mode)}" if mode else ""
    return (f'<div class="pc-booth-head"><div class="pc-brand">{px("seal", " pc-px--lg")} Puesto de Control</div>'
            f'<span class="pc-term">{e(state)}{extra}</span></div>')
