"""Optimize operations: compress, repair, PDF/A."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pymupdf

from .. import toolchain
from ..config import MAX_PAGES, OP_TIMEOUT
from ..util import OpError, guard_pages, safe_stem


def _guard(path: Path) -> None:
    """Refuse oversized documents before spending CPU on them."""
    try:
        with pymupdf.open(str(path)) as doc:
            guard_pages(doc, path.name, MAX_PAGES)
    except OpError:
        raise
    except Exception:
        return

_GS_SETTINGS = {"low": "/prepress", "rec": "/ebook", "strong": "/screen"}


def _gs(*args: str) -> None:
    exe = toolchain.find_ghostscript()
    if not exe:
        raise OpError(
            "Ghostscript belum terpasang di komputer ini. "
            "Lihat panduan setup, bagian memasang program pendukung."
        )
    cmd = [exe, "-dNOPAUSE", "-dQUIET", "-dBATCH", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=OP_TIMEOUT)
    except FileNotFoundError as exc:
        raise OpError("Ghostscript tidak terpasang di server.") from exc
    except subprocess.TimeoutExpired as exc:
        raise OpError("Proses melebihi batas waktu.") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "ignore").strip().splitlines()
        raise OpError(detail[-1] if detail else "Ghostscript gagal memproses file.")


def compress(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    _guard(src)
    level = str(opts.get("level", "rec"))
    setting = _GS_SETTINGS.get(level, "/ebook")
    out = out_dir / f"{safe_stem(src.name)}-kompres.pdf"
    _gs(
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.7",
        f"-dPDFSETTINGS={setting}",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        f"-sOutputFile={out}",
        str(src),
    )
    # Honesty rule from the PRD: never hand back a bigger file than the input.
    if not out.exists() or out.stat().st_size >= src.stat().st_size:
        out.unlink(missing_ok=True)
        fallback = out_dir / f"{safe_stem(src.name)}-kompres.pdf"
        with pymupdf.open(str(src)) as doc:
            doc.save(str(fallback), garbage=4, deflate=True)
        return [fallback]
    return [out]


def repair(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    out = out_dir / f"{safe_stem(src.name)}-perbaikan.pdf"
    _guard(src)
    try:
        with pymupdf.open(str(src)) as doc:
            doc.save(str(out), garbage=4, deflate=True, clean=True)
        if out.exists() and out.stat().st_size > 0:
            return [out]
    except Exception:
        pass
    # Fall back to a Ghostscript rewrite, which also rebuilds broken xref tables.
    _gs(
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.7",
        f"-sOutputFile={out}",
        str(src),
    )
    return [out]


def pdfa(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    src = inputs[0]
    out = out_dir / f"{safe_stem(src.name)}-pdfa.pdf"
    _guard(src)
    lib = toolchain.find_ghostscript_lib()
    base = [
        "-dPDFA=2",
        "-dBATCH",
        "-dNOPAUSE",
        "-sColorConversionStrategy=RGB",
        "-dPDFACompatibilityPolicy=1",
        "-sDEVICE=pdfwrite",
    ]
    if lib is not None:
        # Ghostscript only stamps the PDF/A label when its definition file and
        # the sRGB profile are on its search path, and they sit next to the
        # binary, not on any system path.
        icc = lib / "srgb.icc"
        base += [
            "-sOutputFile=" + str(out),
            f"-I{lib}",
        ]
        if icc.is_file():
            base += [f"-sOutputICCProfile={icc}"]
        base += [str(src)]
        _gs(*base)
    else:
        # Without a PDF/A definition file, emit a normal, cleaned PDF rather
        # than a file that claims a conformance it does not meet.
        _gs("-sDEVICE=pdfwrite", f"-sOutputFile={out}", str(src))
    return [out]
