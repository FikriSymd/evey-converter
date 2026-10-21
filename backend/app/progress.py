"""Per-job progress reporting for long operations.

A handler that wants to report progress binds a file path for the duration of
its run and calls :func:`emit`. The path is held in thread-local storage, so
two jobs running on different worker threads never write to each other's file,
and a job that reports nothing costs nothing.

The progress file lives inside the job directory, which the sweeper deletes
with the job, so progress data never outlives the one hour TTL either.

OCRmyPDF reports each phase in its own unit: the scanning and OCR passes count
pages, while the optimization passes report percent. Raw values therefore jump
backwards between phases (25 pages done, then 0 percent). :data:`STAGES` pins
each phase to a band of the overall 0-100 range and the reported percentage is
clamped so it only ever moves forward.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

_state = threading.local()

# Each phase gets a slice of the overall bar, and a stable key the frontend
# translates. Keys are lowercase matches on the phase description OCRmyPDF
# passes to the progress bar.
STAGES: dict[str, tuple[str, float, float]] = {
    "menyiapkan ocr": ("prep", 0, 3),
    "scanning contents": ("scan", 3, 10),
    "ocr": ("ocr", 10, 88),
    "pdf/a conversion": ("optimize", 88, 92),
    "recompressing jpegs": ("optimize", 88, 92),
    "deflating jpegs": ("optimize", 88, 92),
    "jbig2": ("optimize", 88, 92),
    "pngs": ("optimize", 88, 92),
    "linearizing": ("finalize", 92, 97),
    "checking output": ("finalize", 97, 100),
}
_FALLBACK = ("working", 0, 100)


def bind(path: Path) -> None:
    """Point this thread's progress reports at ``path``."""
    _state.path = str(path)
    _state.last = 0
    _state.current = 0.0
    _state.total = None


def unbind() -> None:
    _state.path = None
    _state.last = 0
    _state.current = 0.0
    _state.total = None


def reconcile(total: float | None) -> None:
    """Adopt the phase's total when it changes.

    OCRmyPDF announces each phase's total at its start, but builds a fresh
    progress bar per phase while this module keeps one accumulator per job, so
    the counter restarts when a new, non-empty total arrives.
    """
    if not total:
        return
    if getattr(_state, "total", None) != total:
        _state.total = total
        _state.current = 0.0


def reset(total: float | None, stage: str) -> None:
    """Start a phase: adopt its total and report the zero point."""
    if total:
        _state.total = total
    _state.current = 0.0
    emit(0, getattr(_state, "total", None), stage)


def advance(increment: float, completed: float | None, total: float | None, stage: str) -> None:
    """Count one progress step.

    ``increment`` is the value OCRmyPDF's progress bar passes to ``update``,
    and it is an *increment*, not a position: the OCR pass calls
    ``update(0.5)`` once per half page and never passes ``completed``. Reading
    it as an absolute position is what leaves a naive progress bar frozen at
    0.5 for the whole scan. Accumulating is what a real bar does.
    """
    reconcile(total)
    if completed is not None:
        _state.current = completed
    else:
        _state.current = getattr(_state, "current", 0.0) + (increment or 0)
    emit(_state.current, getattr(_state, "total", None), stage)


def emit(done: float, total: float | None, stage: str = "") -> None:
    """Record a snapshot; a no-op when no path is bound to this thread.

    ``done``/``total`` are in the phase's own unit. The stored ``pct`` is the
    overall percentage, never lower than the previous one.
    """
    path = getattr(_state, "path", None)
    if not path:
        return

    key, low, high = STAGES.get(stage.strip().lower(), _FALLBACK)
    local = (done / total) if total else 0.0
    local = min(1.0, max(0.0, local))
    pct = int(round(low + (high - low) * local))

    last = getattr(_state, "last", 0)
    pct = max(pct, last)
    _state.last = pct

    payload = {"pct": pct, "stage": key, "label": stage}
    target = Path(path)
    try:
        # Write then move, so a reader never sees a half-written snapshot.
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        tmp.replace(target)
    except OSError:
        # Progress is a nicety: never let a write failure break the job.
        pass


def read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None