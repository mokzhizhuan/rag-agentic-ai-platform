"""Per-generation progress events, isolated using ContextVar.

Only the generation worker attaches a database callback. Other callers are unaffected.
"""
from contextvars import ContextVar
from typing import Callable, Optional

_sink: ContextVar[Optional[Callable[[str, int], None]]] = ContextVar('artifact_progress_sink', default=None)


def bind_progress(callback):
    return _sink.set(callback)


def reset_progress(token):
    _sink.reset(token)


def report_progress(stage: str, percent: int):
    callback = _sink.get()
    if callback is not None:
        callback(str(stage)[:240], max(0, min(99, int(percent))))
