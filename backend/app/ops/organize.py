"""Organize operations: merge, split, reorder, rotate, remove, extract."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from ..config import MAX_PAGES
from ..util import OpError, guard_pages, parse_order, parse_page_range, safe_stem


def _open(path: Path) -> "pymupdf.Document":
    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:  # corrupt / unreadable
        raise OpError(f"PDF '{path.name}' tidak bisa dibuka.") from exc
    guard_pages(doc, path.name, MAX_PAGES)
    return doc


def merge(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    out = out_dir / "gabungan.pdf"
    merged = pymupdf.open()
    try:
        for src in inputs:
            with _open(src) as doc:
                merged.insert_pdf(doc)
        merged.save(str(out), garbage=4, deflate=True)
    finally:
        merged.close()
    return [out]


def split(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    mode = str(opts.get("mode", "range"))
    with _open(src) as doc:
        n = doc.page_count
        stem = safe_stem(src.name)
        if mode == "pages":
            outputs = []
            for i in range(n):
                part = pymupdf.open()
                part.insert_pdf(doc, from_page=i, to_page=i)
                dest = out_dir / f"{stem}-hal{i + 1:03d}.pdf"
                part.save(str(dest), garbage=4, deflate=True)
                part.close()
                outputs.append(dest)
            return outputs
        pages = parse_page_range(str(opts.get("range", "")), n)
        part = pymupdf.open()
        for idx in pages:
            part.insert_pdf(doc, from_page=idx, to_page=idx)
        dest = out_dir / f"{stem}-pisah.pdf"
        part.save(str(dest), garbage=4, deflate=True)
        part.close()
        return [dest]


def organize(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    with _open(src) as doc:
        order = parse_order(str(opts.get("order", "")), doc.page_count)
        out = out_dir / f"{safe_stem(src.name)}-urut.pdf"
        result = pymupdf.open()
        for idx in order:
            result.insert_pdf(doc, from_page=idx, to_page=idx)
        result.save(str(out), garbage=4, deflate=True)
        result.close()
    return [out]


def rotate(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    angle = int(str(opts.get("angle", "90")))
    scope = str(opts.get("scope", "all"))
    out = out_dir / f"{safe_stem(src.name)}-putar.pdf"
    with _open(src) as doc:
        targets = (
            parse_page_range(str(opts.get("range", "")), doc.page_count)
            if scope == "range"
            else list(range(doc.page_count))
        )
        for idx in targets:
            page = doc[idx]
            page.set_rotation((page.rotation + angle) % 360)
        doc.save(str(out), garbage=4, deflate=True)
    return [out]


def remove_pages(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    with _open(src) as doc:
        drop = set(parse_page_range(str(opts.get("range", "")), doc.page_count))
        keep = [i for i in range(doc.page_count) if i not in drop]
        if not keep:
            raise OpError("Semua halaman dihapus. Sisakan minimal satu halaman.")
        out = out_dir / f"{safe_stem(src.name)}-hapus.pdf"
        result = pymupdf.open()
        for idx in keep:
            result.insert_pdf(doc, from_page=idx, to_page=idx)
        result.save(str(out), garbage=4, deflate=True)
        result.close()
    return [out]


def extract_pages(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    with _open(src) as doc:
        pages = parse_page_range(str(opts.get("range", "")), doc.page_count)
        out = out_dir / f"{safe_stem(src.name)}-ekstrak.pdf"
        result = pymupdf.open()
        for idx in pages:
            result.insert_pdf(doc, from_page=idx, to_page=idx)
        result.save(str(out), garbage=4, deflate=True)
        result.close()
    return [out]
