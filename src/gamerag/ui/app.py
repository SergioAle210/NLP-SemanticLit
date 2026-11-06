"""Frontend mínimo (Streamlit) sobre la API: juego, perfil, pregunta, respuesta con citas y traza.

Uso (con la API corriendo en otra terminal):
    uv run uvicorn gamerag.api:app
    uv run --extra ui streamlit run src/gamerag/ui/app.py

La URL de la API se toma de GAMERAG_API_URL (por defecto http://127.0.0.1:8000) y el juego
preseleccionado de GAMERAG_UI_DEFAULT_GAME (por defecto zelda1).
Es una interfaz de demo y depuración; el diseño definitivo se hace aparte contra la misma API.
"""

from __future__ import annotations

import os

import streamlit as st

from gamerag.ui.client import ApiClient, ApiError, audit_row, describe_progress, hit_label

st.set_page_config(page_title="GameRAG", page_icon="🎮", layout="wide")


@st.cache_resource
def get_client() -> ApiClient:
    return ApiClient()


@st.cache_data(ttl=30)
def load_catalog() -> tuple[dict, list[dict], list[dict]]:
    c = get_client()
    return c.health(), c.games(), c.profiles()


client = get_client()

# --- barra lateral: estado, juego y perfil ---------------------------------------------------
with st.sidebar:
    st.title("🎮 GameRAG")
    try:
        health, games, profiles = load_catalog()
    except ApiError as e:
        st.error(f"API no disponible.\n\n{e.detail}\n\nLevántala con `uv run uvicorn gamerag.api:app`.")
        st.stop()

    available = [g for g in games if g["available"]]
    if not available:
        st.error("La API no tiene ningún juego indexado: corre la ingesta.")
        st.stop()
    # Juego principal por defecto (si no, el primero alfabético sería Ninja Gaiden).
    ids = [g["game_id"] for g in available]
    default = os.environ.get("GAMERAG_UI_DEFAULT_GAME", "zelda1")
    game = st.selectbox("Juego", available, index=ids.index(default) if default in ids else 0,
                        format_func=lambda g: f"{g['title']} ({g['year']})")
    profile = st.selectbox("Perfil (progreso del jugador)", profiles, format_func=lambda p: p["user_id"])
    st.caption(describe_progress(profile, game["game_id"]))
    mode = st.radio("Modo", ["Responder", "Solo buscar"], horizontal=True,
                    help="Responder: /ask (pregunta → respuesta con citas). "
                         "Solo buscar: /search (el contexto que recibiría el generador, sin generar).")
    st.divider()
    st.caption(f"API {client.base_url} · v{health['version']}\n\n"
               f"Recuperación: `{health['retriever']}` · Generador: `{health['generator']}`")

tab_ask, tab_audit = st.tabs(["Preguntar", "Auditoría (admin)"])


def show_hits(hits: list[dict]) -> None:
    # Una sección larga se divide en varios chunks con el mismo nombre de sección: la etiqueta lleva el
    # chunk_id y el inicio del texto para distinguirlos.
    for h in hits:
        with st.expander(f"#{h['rank']} · {hit_label(h)}  (score {h['score']})"):
            st.text(h["text"])
            st.caption(f"`{h['chunk_id']}` · [fuente]({h['url']})")


def show_trace(trace: dict) -> None:
    st.markdown(f"**Resultado:** `{trace['outcome']}` · **ruta:** `{trace.get('route', 'documents')}` · "
                f"**traza:** `{trace['trace_id']}`")
    if len(trace.get("query_variants", [])) > 1:
        st.markdown("**Variantes de la consulta** (multi-consulta):")
        for v in trace["query_variants"]:
            st.markdown(f"- {v}")
    cols = st.columns(2)
    cols[0].markdown("**Guards de entrada**")
    cols[0].json(trace.get("input_guards", {}), expanded=False)
    cols[1].markdown("**Guards de salida**")
    cols[1].json(trace.get("output_guards", {}), expanded=False)
    st.markdown("**Latencia por etapa (ms)**")
    st.dataframe([trace.get("latency_ms", {})], hide_index=True)
    st.markdown(f"**Candidatos** ({len(trace.get('candidates', []))}; los bloqueados por un filtro tienen "
                f"`blocked_by`) · **contexto entregado:** {', '.join(trace.get('context', [])) or '—'}")
    st.dataframe(trace.get("candidates", []), hide_index=True)


# --- pestaña principal --------------------------------------------------------------------------
with tab_ask:
    with st.form("ask"):
        question = st.text_input("Pregunta (en inglés)", placeholder="How do I get the raft?", max_chars=500)
        submitted = st.form_submit_button("Preguntar", type="primary")

    if submitted and question.strip():
        args = (question.strip(), game["game_id"], profile["user_id"])
        try:
            with st.spinner("Buscando…"):
                if mode == "Responder":
                    result = client.ask(*args)
                    # El contexto con texto completo sale de /search (misma búsqueda, determinista).
                    # Si respondió una herramienta, no hubo búsqueda documental: no se muestra contexto.
                    context = None if result["answer"].get("tool_used") else client.search(*args)
                else:
                    result, context = None, client.search(*args)
        except ApiError as e:
            st.error(f"La API respondió con error {e.status}: {e.detail}")
            st.stop()

        if result is not None:
            ans = result["answer"]
            if ans.get("blocked_by_spoiler"):
                st.warning("🔒 " + ans["answer"])
            elif ans["abstained"]:
                st.info(ans["answer"])
            else:
                st.success(ans["answer"])
            if ans.get("needs_human_review"):
                st.caption("⚠️ Marcada para revisión humana.")
            if ans.get("sources"):
                st.markdown("**Citas:** " + " · ".join(f"`{s['source']}` (`{s['chunk_id']}`)" for s in ans["sources"]))
            trace = result["trace"]
        else:
            trace = context["trace"]

        if context is None:
            tool = trace.get("tool") or {}
            st.subheader(f"Herramienta: `{tool.get('name')}`")
            st.caption(f"Router: {trace.get('route_reason', '')}")
            st.json(tool, expanded=True)
        else:
            st.subheader("Contexto recuperado")
            if context["hits"]:
                show_hits(context["hits"])
            else:
                st.caption("Sin fragmentos (la pregunta fue rechazada o bloqueada).")

        with st.expander("Traza (auditoría)"):
            show_trace(trace)

# --- auditoría ----------------------------------------------------------------------------------
with tab_audit:
    if profile["role"] != "admin":
        st.info("Selecciona el perfil `admin` en la barra lateral para ver el log de auditoría.")
    else:
        limit = st.slider("Últimas consultas", 5, 100, 20)
        try:
            rows = client.audit(profile["user_id"], limit)
        except ApiError as e:
            st.error(f"{e.status}: {e.detail}")
        else:
            st.caption("Las preguntas se guardan con la PII redactada (correo, teléfono, claves).")
            st.dataframe([audit_row(r) for r in rows], hide_index=True)
