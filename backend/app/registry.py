"""Tool registry: maps catalog IDs to handlers and input kinds.

The IDs must match the frontend catalog in app.js one-for-one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .ops import convert, optimize, organize, security
from .util import OpError

Handler = Callable[[list, dict, object], list]


@dataclass(frozen=True)
class Tool:
    id: str
    kind: str  # pdf | docx | xlsx | pptx | image | html
    handler: Handler
    multiple: bool = True


TOOLS: dict[str, Tool] = {
    # Organize
    "merge": Tool("merge", "pdf", organize.merge, True),
    "split": Tool("split", "pdf", organize.split, False),
    "organize": Tool("organize", "pdf", organize.organize, False),
    "rotate": Tool("rotate", "pdf", organize.rotate, False),
    "remove_pages": Tool("remove_pages", "pdf", organize.remove_pages, False),
    "extract_pages": Tool("extract_pages", "pdf", organize.extract_pages, False),
    # Optimize
    "compress": Tool("compress", "pdf", optimize.compress, True),
    "repair": Tool("repair", "pdf", optimize.repair, True),
    "pdfa": Tool("pdfa", "pdf", optimize.pdfa, True),
    # Convert
    "pdf_word": Tool("pdf_word", "pdf", convert.pdf_word, True),
    "pdf_excel": Tool("pdf_excel", "pdf", convert.pdf_excel, True),
    "pdf_ppt": Tool("pdf_ppt", "pdf", convert.pdf_ppt, True),
    "word_pdf": Tool("word_pdf", "docx", convert.word_pdf, True),
    "excel_pdf": Tool("excel_pdf", "xlsx", convert.excel_pdf, True),
    "ppt_pdf": Tool("ppt_pdf", "pptx", convert.ppt_pdf, True),
    "pdf_jpg": Tool("pdf_jpg", "pdf", convert.pdf_jpg, True),
    "jpg_pdf": Tool("jpg_pdf", "image", convert.jpg_pdf, True),
    "html_pdf": Tool("html_pdf", "html", convert.html_pdf, False),
    "ocr": Tool("ocr", "pdf", convert.ocr, True),
    # Security
    "protect": Tool("protect", "pdf", security.protect, True),
    "unlock": Tool("unlock", "pdf", security.unlock, True),
    "watermark": Tool("watermark", "pdf", security.watermark, True),
}


def get(tool_id: str) -> Tool:
    tool = TOOLS.get(tool_id)
    if tool is None:
        raise OpError(f"Tool '{tool_id}' tidak dikenal.")
    return tool
