"""Shared helpers: page ranges, filenames, zip packing."""

from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path


class OpError(Exception):
    """An error with a message that is safe to show to the user."""


def parse_page_range(spec: str, n_pages: int) -> list[int]:
    """'1-3,5' -> [0,1,2,4]. Accepts open ends like '3-' and '-2'."""
    spec = (spec or "").strip()
    if not spec:
        raise OpError("Rentang halaman kosong.")
    picked: list[int] = []
    for raw in spec.replace(" ", "").split(","):
        if not raw:
            continue
        if "-" in raw:
            a, _, b = raw.partition("-")
            try:
                start = int(a) if a else 1
                end = int(b) if b else n_pages
            except ValueError as exc:
                raise OpError(f"Rentang '{raw}' tidak valid.") from exc
            if start < 1 or end > n_pages or start > end:
                raise OpError(f"Rentang '{raw}' di luar halaman 1-{n_pages}.")
            picked.extend(range(start - 1, end))
        else:
            try:
                page = int(raw)
            except ValueError as exc:
                raise OpError(f"Halaman '{raw}' tidak valid.") from exc
            if page < 1 or page > n_pages:
                raise OpError(f"Halaman {page} di luar jangkauan 1-{n_pages}.")
            picked.append(page - 1)
    seen: set[int] = set()
    ordered: list[int] = []
    for idx in picked:
        if idx not in seen:
            seen.add(idx)
            ordered.append(idx)
    if not ordered:
        raise OpError("Tidak ada halaman yang dipilih.")
    return ordered


def parse_order(spec: str, n_pages: int) -> list[int]:
    """'3,1,2' -> [2,0,1]. Pages may repeat."""
    spec = (spec or "").strip()
    if not spec:
        raise OpError("Urutan halaman kosong.")
    order: list[int] = []
    for raw in spec.replace(" ", "").split(","):
        if not raw:
            continue
        try:
            page = int(raw)
        except ValueError as exc:
            raise OpError(f"Urutan '{raw}' tidak valid.") from exc
        if page < 1 or page > n_pages:
            raise OpError(f"Halaman {page} di luar jangkauan 1-{n_pages}.")
        order.append(page - 1)
    if not order:
        raise OpError("Tidak ada halaman pada urutan.")
    return order


_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
_INDEX_PREFIX = re.compile(r"^\d{3,}-")


def safe_stem(name: str) -> str:
    """A filename stem safe for the filesystem and Content-Disposition."""
    stem = Path(name).stem
    stem = _INDEX_PREFIX.sub("", stem)  # drop the upload de-dup prefix
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    stem = _SAFE.sub("-", stem).strip("-._")
    return stem or "file"


def zip_outputs(paths: list[Path], out_path: Path) -> Path:
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, arcname=path.name)
    return out_path


def guard_pages(doc, name: str, limit: int) -> None:
    """Refuse a PDF with more pages than the service is willing to chew.

    A page count is the cheapest proxy for how much work a document implies,
    and it is known before any real processing starts.
    """
    if doc.page_count > limit:
        raise OpError(
            f"'{name}' punya {doc.page_count} halaman, melebihi batas {limit} halaman."
        )
