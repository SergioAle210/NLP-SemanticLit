"""Captura por solicitud, independiente de clientes y libros de gasto compartidos."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps


@dataclass
class Capture:
    trace_id: str
    calls: list[dict] = field(default_factory=list)
    degradations: list[dict] = field(default_factory=list)
    stages: list[dict] = field(default_factory=list)


_capture: ContextVar[Capture | None] = ContextVar("gamerag_capture", default=None)
_stage: ContextVar[str] = ContextVar("gamerag_stage", default="unspecified")


def current_capture() -> Capture | None:
    return _capture.get()


@contextmanager
def request_scope(trace_id: str | None = None) -> Iterator[Capture]:
    """Reutiliza el ámbito exterior del benchmark; cada solicitud raíz crea sus propias listas."""
    existing = current_capture()
    if existing is not None:
        yield existing
        return
    capture = Capture(trace_id or uuid.uuid4().hex)
    token = _capture.set(capture)
    try:
        yield capture
    finally:
        _capture.reset(token)


def record_call(**values) -> None:
    if capture := current_capture():
        capture.calls.append({"stage": _stage.get(), **values})


def record_degradation(**values) -> None:
    if capture := current_capture():
        capture.degradations.append({"stage": _stage.get(), **values})


def observed(name: str):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with stage(name):
                return fn(*args, **kwargs)
        return wrapped
    return decorate


@contextmanager
def stage(name: str) -> Iterator[None]:
    token = _stage.set(name)
    start = time.perf_counter()
    event = {"name": name, "status": "ok"}
    try:
        yield
    except Exception as exc:
        event.update(status="error", error_type=type(exc).__name__)
        raise
    finally:
        event["duration_ms"] = round(1000 * (time.perf_counter() - start), 3)
        if capture := current_capture():
            capture.stages.append(event)
        _stage.reset(token)
