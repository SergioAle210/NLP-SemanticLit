"""Cliente HTTP de la API. La interfaz solo habla con la API (nunca importa el pipeline), así que
cualquier otro frontend puede reemplazarla usando los mismos endpoints.

Se separa de `app.py` para poder probarlo sin Streamlit: los tests le pasan el `TestClient` de
FastAPI, que es un `httpx.Client`.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_API_URL = "http://127.0.0.1:8000"


class ApiError(RuntimeError):
    """Error de la API con su código HTTP y el detalle que devolvió."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


class ApiClient:
    def __init__(self, base_url: str | None = None, client: httpx.Client | None = None, timeout: float = 60.0):
        self.base_url = (base_url or os.environ.get("GAMERAG_API_URL") or DEFAULT_API_URL).rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url, timeout=timeout)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            r = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as e:  # API caída, timeout, DNS…
            raise ApiError(0, f"no se pudo conectar con la API en {self.base_url} ({e})") from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ApiError(r.status_code, str(detail))
        return r.json()

    # --- catálogo y perfiles ---
    def health(self) -> dict:
        return self._request("GET", "/health")

    def games(self) -> list[dict]:
        return self._request("GET", "/games")

    def profiles(self) -> list[dict]:
        return self._request("GET", "/profiles")

    # --- consulta ---
    def ask(self, question: str, game: str, user_id: str) -> dict:
        """Respuesta con citas + traza."""
        return self._request("POST", "/ask", json={"question": question, "game": game, "user_id": user_id,
                                                   "include_trace": True})

    def search(self, question: str, game: str, user_id: str) -> dict:
        """Contexto que recibe el generador (sin generar)."""
        return self._request("POST", "/search", json={"question": question, "game": game, "user_id": user_id})

    # --- admin ---
    def audit(self, user_id: str, limit: int = 20) -> list[dict]:
        return self._request("GET", "/audit", params={"user_id": user_id, "limit": limit})


def hit_label(hit: dict, preview_words: int = 10) -> str:
    """Etiqueta de un fragmento: página › sección · chunk_id · inicio del texto.

    Varias partes de una sección larga comparten el nombre de sección; el chunk_id y el inicio del texto
    las distinguen. Se quita el encabezado "[Sección]" que la ingesta pone al principio del texto."""
    page = hit["source"].partition("/")[2] or hit["source"]  # sin el nombre del juego
    short_id = hit["chunk_id"].partition(":")[2] or hit["chunk_id"]
    body = " ".join(line for line in hit["text"].splitlines() if not line.startswith("["))
    words = body.split()
    preview = " ".join(words[:preview_words]) + ("…" if len(words) > preview_words else "")
    return f"{page} › {hit['section']} · {short_id} — “{preview}”"


def audit_row(trace: dict) -> dict:
    """Fila plana de la tabla de auditoría (la traza completa trae listas y diccionarios anidados)."""
    return {
        "fecha": trace.get("created_at"),
        "usuario": trace.get("user_id"),
        "juego": trace.get("game"),
        "pregunta": trace.get("question"),
        "resultado": trace.get("outcome"),
        "contexto": len(trace.get("context", [])),
        "bloqueados": sum(1 for c in trace.get("candidates", []) if c.get("blocked_by")),
        "ms": round(sum(trace.get("latency_ms", {}).values()), 1),
    }


def describe_progress(profile: dict, game_id: str) -> str:
    """Resumen legible del progreso de un perfil en un juego (para la barra lateral)."""
    if profile.get("role") in ("completionist", "admin"):
        return f"rol {profile['role']}: sin restricciones de spoilers"
    p = (profile.get("progress") or {}).get(game_id)
    if not p:
        return "sin progreso registrado en este juego"
    if p.get("kind") == "level_set":
        done = ", ".join(map(str, p.get("completed_levels") or [])) or "ninguno"
        return f"quest {p.get('quest')} · niveles completados: {done} · actual: {p.get('current_level')}"
    if p.get("kind") == "linear_stage":
        return f"etapa actual: {p.get('current_stage')}"
    return str(p)
