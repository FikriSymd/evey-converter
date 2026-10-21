"""OCRmyPDF plugin: relay its progress bar into the job's progress file.

Registered by module name (``plugins=["app.ocr_plugin"]``) from convert.ocr,
so this module is imported inside the backend process where ``app.progress``
resolves. The bar reports an increment per completed unit of work, never an
absolute position; :func:`progress.advance` does the counting.
"""

from __future__ import annotations

from ocrmypdf import hookimpl
from ocrmypdf.pluginspec import ProgressBar

from .progress import advance, emit, reset


class JobProgressBar(ProgressBar):
    def __init__(self, *, total=None, desc=None, unit=None, disable=False, **kwargs):
        self.total = total
        self.desc = desc or ""
        reset(total, self.desc)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def update(self, n=1, *, completed=None, total=None):
        advance(n, completed, total or self.total, self.desc)

    def reset(self, **kwargs):
        self.total = kwargs.get("total", self.total)

    def set_description(self, desc):
        self.desc = desc


@hookimpl
def get_progressbar_class():
    return JobProgressBar