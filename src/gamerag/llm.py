"""Cliente de LLM con control de costo: tope duro, libro de gastos y caché en disco.

Todo acceso a Claude (generador, router, evaluador, juez de evaluación) debe pasar por `LLMClient`:

- **Tope duro** (`llm_budget_usd`) acumulado entre corridas, y tope por corrida (`run`). Antes de cada
  llamada se estima el peor caso (entrada + `max_tokens`); si no cabe, lanza `BudgetExceeded` sin llamar.
- **Libro de gastos** en SQLite (`state/llm_usage.sqlite3`): una fila por llamada, con tokens y costo.
- **Caché en disco** por solicitud (modelo + system + mensajes + parámetros): una repetición cuesta $0.
  Con `llm_offline=True` solo se sirve de la caché (una falla de caché lanza `CacheMiss`): sirve para
  repetir evaluaciones y correr tests sin gastar.

Los precios son configurables (`llm_price_*`, USD por millón de tokens). Los valores por defecto son una
estimación conservadora: verifícalos contra la consola de Anthropic. El libro estima el gasto; el saldo
real solo lo da la consola.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

from gamerag.settings import Settings, get_settings

log = logging.getLogger(__name__)


class BudgetExceeded(RuntimeError):
    """La llamada no cabe en el tope total o en el de la corrida."""


class CacheMiss(RuntimeError):
    """Modo sin conexión (`llm_offline`) y la solicitud no está en la caché."""


class Ledger:
    """Libro de gastos: una fila por llamada."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, run TEXT, "
                "model TEXT, input_tokens INTEGER, output_tokens INTEGER, cache_read INTEGER, "
                "cache_write INTEGER, cost_usd REAL, cached INTEGER)"
            )

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(self, *, run: str, model: str, usage: dict, cost: float, cached: bool) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO calls (ts, run, model, input_tokens, output_tokens, cache_read, cache_write, "
                "cost_usd, cached) VALUES (?,?,?,?,?,?,?,?,?)",
                (time.time(), run, model, usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                 usage.get("cache_read", 0), usage.get("cache_write", 0), cost, int(cached)),
            )

    def spent(self, run: str | None = None, since: float | None = None) -> float:
        """Gasto acumulado; con `run`, el de esa etiqueta (desde `since`: el tope por corrida es por proceso)."""
        with self._conn() as c:
            if run is not None and since is not None:
                row = c.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM calls WHERE run = ? AND ts >= ?",
                                (run, since)).fetchone()
            elif run is None:
                row = c.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM calls").fetchone()
            else:
                row = c.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM calls WHERE run = ?", (run,)).fetchone()
        return float(row[0])

    def summary(self) -> dict:
        with self._conn() as c:
            n, inp, out, cost, hits = c.execute(
                "SELECT COUNT(*), COALESCE(SUM(input_tokens),0), COALESCE(SUM(output_tokens),0), "
                "COALESCE(SUM(cost_usd),0), COALESCE(SUM(cached),0) FROM calls"
            ).fetchone()
        return {"calls": n, "cache_hits": hits, "input_tokens": inp, "output_tokens": out,
                "spent_usd": round(cost, 4)}


class LLMClient:
    def __init__(self, settings: Settings | None = None, *, client: Any = None, ledger: Ledger | None = None):
        self.s = settings or get_settings()
        self._client = client  # inyectable en tests; si no, se crea perezosamente
        self.ledger = ledger or Ledger(self.s.path(self.s.llm_usage_db))
        self.cache_dir = self.s.path(self.s.llm_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._t0 = time.time()  # inicio de este cliente: el tope por corrida solo cuenta desde aqui

    # --- costo -------------------------------------------------------------------------------

    def _cost(self, usage: dict) -> float:
        p = self.s
        return (usage.get("input_tokens", 0) * p.llm_price_input
                + usage.get("output_tokens", 0) * p.llm_price_output
                + usage.get("cache_read", 0) * p.llm_price_input * 0.1
                + usage.get("cache_write", 0) * p.llm_price_input * 1.25) / 1_000_000

    def _worst_case(self, payload: dict) -> float:
        # ~3 caracteres por token: sobreestima a propósito (más seguro para un tope).
        in_tokens = len(json.dumps(payload, ensure_ascii=False)) / 3
        return self._cost({"input_tokens": in_tokens, "output_tokens": payload["max_tokens"]})

    def _check_budget(self, payload: dict, run: str) -> None:
        need = self._worst_case(payload)
        total = self.ledger.spent()
        if total + need > self.s.llm_budget_usd:
            raise BudgetExceeded(f"tope total: gastado ${total:.4f} + peor caso ${need:.4f} "
                                 f"> ${self.s.llm_budget_usd:.2f}")
        in_run = self.ledger.spent(run, since=self._t0)  # tope por corrida = por proceso; el total es acumulado
        if in_run + need > self.s.llm_run_budget_usd:
            raise BudgetExceeded(f"tope de la corrida '{run}': gastado ${in_run:.4f} + peor caso "
                                 f"${need:.4f} > ${self.s.llm_run_budget_usd:.2f}")

    # --- llamada -----------------------------------------------------------------------------

    def complete(self, messages: list[dict], *, system: str | list | None = None, max_tokens: int = 512,
                 temperature: float | None = None, tools: list[dict] | None = None,
                 tool_choice: dict | None = None, output_config: dict | None = None,
                 model: str | None = None, run: str = "default") -> Any:
        """Devuelve el `Message` de Anthropic (de la caché o de la API) y registra el gasto.

        `temperature` se omite por defecto: los modelos 5.x rechazan valores distintos del predeterminado.
        `output_config` admite `{"effort": "low"}` y `{"format": {...json_schema...}}`.
        """
        payload: dict[str, Any] = {
            "model": model or self.s.llm_model,
            "max_tokens": min(max_tokens, self.s.llm_max_tokens),
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if output_config:
            payload["output_config"] = output_config
        if system is not None:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice

        key = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        cache_file = self.cache_dir / f"{key}.json"
        if self.s.llm_cache and cache_file.exists():
            msg = self._parse(json.loads(cache_file.read_text(encoding="utf-8")))
            self.ledger.record(run=run, model=payload["model"], usage={}, cost=0.0, cached=True)
            return msg
        if self.s.llm_offline:
            raise CacheMiss("llm_offline=True y la solicitud no está en la caché")

        self._check_budget(payload, run)
        msg = self._api().messages.create(**payload)
        u = msg.usage
        usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                 "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                 "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0}
        cost = self._cost(usage)
        self.ledger.record(run=run, model=payload["model"], usage=usage, cost=cost, cached=False)
        if self.s.llm_cache:
            cache_file.write_text(json.dumps(msg.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
        log.info("llm %s run=%s in=%d out=%d $%.5f (acumulado $%.4f)", payload["model"], run,
                 usage["input_tokens"], usage["output_tokens"], cost, self.ledger.spent())
        return msg

    def _api(self):
        if self._client is None:
            import anthropic

            if self.s.anthropic_api_key is None:
                raise RuntimeError("falta ANTHROPIC_API_KEY (ver .env.example)")
            self._client = anthropic.Anthropic(api_key=self.s.anthropic_api_key.get_secret_value(),
                                               max_retries=2, timeout=60.0)
        return self._client

    @staticmethod
    def _parse(data: dict) -> Any:
        from anthropic.types import Message

        return Message.model_validate(data)

    @staticmethod
    def text(msg: Any) -> str:
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
