"""Estado persistente en SQLite: perfiles de demo y log de auditoría (ADR-0004).

- `profiles`: se siembra desde data/seed/profiles.json si está vacía; `reset_profiles` la restablece.
- `audit`: una fila por consulta con la traza completa del pipeline (§5.8: trazabilidad), con la
  pregunta **redactada** de PII antes de guardarse (§5.8: sanitización en logs).

SQLite es un archivo (state/gamerag.sqlite3, en un volumen en Docker): sin servidor ni recursos extra.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from gamerag.pipeline import Trace
from gamerag.progress.models import Profile

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    user_id TEXT PRIMARY KEY,
    data    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    trace_id   TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    game       TEXT NOT NULL,
    question   TEXT NOT NULL,      -- redactada
    outcome    TEXT NOT NULL,
    trace      TEXT NOT NULL       -- JSON de Trace, con la pregunta redactada
);
CREATE INDEX IF NOT EXISTS audit_created ON audit(created_at);
"""

# Redacción mínima de PII para los logs. Los detectores más completos son parte del InputGuard de PII
# (docs/contracts/access-and-guardrails.md); esto garantiza que lo obvio nunca llegue al log.
_PII_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[PHONE]"),
    (re.compile(r"\b(sk-ant-[\w-]+|sk-[\w-]{20,})\b"), "[SECRET]"),  # claves de API pegadas por error
]


def redact_pii(text: str) -> str:
    for pattern, repl in _PII_PATTERNS:
        text = pattern.sub(repl, text)
    return text


class Store:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        # check_same_thread=False: FastAPI puede atender desde distintos hilos; las escrituras son
        # transacciones cortas y SQLite serializa los escritores.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # --- perfiles ---------------------------------------------------------------------------

    def seed_profiles(self, profiles: dict[str, Profile], overwrite: bool = False) -> int:
        """Inserta los perfiles sembrados. Sin `overwrite`, solo si la tabla está vacía."""
        with self._conn:
            if overwrite:
                self._conn.execute("DELETE FROM profiles")
            elif self._conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]:
                return 0
            self._conn.executemany("INSERT INTO profiles (user_id, data) VALUES (?, ?)",
                                   [(p.user_id, p.model_dump_json()) for p in profiles.values()])
        return len(profiles)

    def get_profile(self, user_id: str) -> Profile | None:
        row = self._conn.execute("SELECT data FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return Profile.model_validate_json(row[0]) if row else None

    def list_profiles(self) -> list[Profile]:
        rows = self._conn.execute("SELECT data FROM profiles ORDER BY user_id").fetchall()
        return [Profile.model_validate_json(r[0]) for r in rows]

    def save_profile(self, profile: Profile) -> None:
        with self._conn:
            self._conn.execute("INSERT OR REPLACE INTO profiles (user_id, data) VALUES (?, ?)",
                               (profile.user_id, profile.model_dump_json()))

    # --- auditoría --------------------------------------------------------------------------

    def log_trace(self, trace: Trace) -> None:
        # Todo campo que contenga texto del usuario se redacta (la pregunta y sus reformulaciones).
        safe = trace.model_copy(update={"question": redact_pii(trace.question),
                                        "query_variants": [redact_pii(v) for v in trace.query_variants]})
        with self._conn:
            self._conn.execute(
                "INSERT INTO audit (trace_id, created_at, user_id, game, question, outcome, trace) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (safe.trace_id, datetime.now(UTC).isoformat(timespec="seconds"), safe.user_id, safe.game,
                 safe.question, safe.outcome, safe.model_dump_json()),
            )

    def recent_traces(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT created_at, trace FROM audit ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"created_at": ts, **json.loads(t)} for ts, t in rows]
