"""Locating the external programs the handlers shell out to.

Ghostscript, LibreOffice and Tesseract are separate installs, and each one is
named differently and lives somewhere else depending on the platform: ``gs``
versus ``gswin64c.exe``, ``/usr/bin/soffice`` versus
``C:\\Program Files\\LibreOffice\\program\\soffice.exe``.

Resolving them once, here, keeps the operation modules free of platform
branching and turns a missing install into a message that names what to
install instead of a bare ``FileNotFoundError``.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

log = logging.getLogger("evey.toolchain")

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"


def _program_files_roots() -> list[Path]:
    """The Program Files roots, the 64-bit one first."""
    roots: list[Path] = []
    for var in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(var)
        if value:
            roots.append(Path(value))
    for fallback in (r"C:\Program Files", r"C:\Program Files (x86)"):
        p = Path(fallback)
        if p.is_dir() and p not in roots:
            roots.append(p)
    return roots


def _sorted_newest(paths) -> list[Path]:
    """Newest-first, so a box with two versions picks the current one."""
    return sorted(paths, key=lambda p: p.name, reverse=True)


# ---- Ghostscript ---------------------------------------------------------

def find_ghostscript() -> str | None:
    """Path to the Ghostscript executable, or None when it is not installed."""
    for name in ("gs", "gswin64c", "gswin32c"):
        found = shutil.which(name)
        if found:
            return found
    candidates: list[Path] = []
    if WINDOWS:
        for root in _program_files_roots():
            gs_root = root / "gs"
            if gs_root.is_dir():
                for pattern in ("gs*/bin/gswin64c.exe", "gs*/bin/gswin32c.exe"):
                    candidates.extend(gs_root.glob(pattern))
    if MACOS:
        for root in (Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
            for name in ("gs", "gswin64c"):
                candidates.extend(root.glob(name))
    if candidates:
        return str(_sorted_newest(candidates)[0])
    return None


def find_ghostscript_lib() -> Path | None:
    """Ghostscript's ``lib`` directory, where ``PDFA_def.ps`` lives.

    Ghostscript needs that PostScript fragment to stamp a PDF as PDF/A, and it
    ships next to the binary rather than anywhere a search path would find it.
    """
    exe = find_ghostscript()
    if exe:
        binary = Path(exe).resolve()
        if WINDOWS:
            # <root>/gs<ver>/bin/gswin64c.exe -> <root>/gs<ver>/lib
            for parent in (binary.parent.parent, binary.parent.parent.parent):
                for name in ("lib", "Resource/Init"):
                    cand = parent / name
                    if (cand / "PDFA_def.ps").is_file():
                        return cand
        else:
            for cand in (binary.parent.parent / "share/ghostscript", binary.parent / "share/ghostscript"):
                if cand.is_dir():
                    for version in _sorted_newest(p for p in cand.iterdir() if p.is_dir()):
                        if (version / "lib/PDFA_def.ps").is_file():
                            return version / "lib"
    # Last resort: the well-known locations, by glob.
    from glob import glob as _glob

    hits = [Path(p) for p in _glob("/usr/share/ghostscript/*/lib/PDFA_def.ps")]
    hits += [Path(p) for p in _glob("/usr/local/share/ghostscript/*/lib/PDFA_def.ps")]
    hits += [Path(p) for p in _glob("/opt/homebrew/share/ghostscript/*/lib/PDFA_def.ps")]
    if WINDOWS:
        for root in _program_files_roots():
            hits += [Path(p) for p in _glob(str(root / "gs" / "gs*" / "lib" / "PDFA_def.ps"))]
    if hits:
        return _sorted_newest(hits)[0].parent
    return None


# ---- LibreOffice ---------------------------------------------------------

def find_soffice() -> str | None:
    """Path to the LibreOffice headless converter."""
    for name in ("soffice", "soffice.exe", "soffice.com", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates: list[Path] = []
    if WINDOWS:
        for root in _program_files_roots():
            candidates.append(root / "LibreOffice" / "program" / "soffice.exe")
            candidates.append(root / "LibreOffice" / "program" / "soffice.com")
    if MACOS:
        candidates.append(Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"))
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


# ---- Tesseract (OCRmyPDF finds it itself, but we report on it) -----------

def find_tesseract() -> str | None:
    for name in ("tesseract", "tesseract.exe"):
        found = shutil.which(name)
        if found:
            return found
    if WINDOWS:
        for root in _program_files_roots():
            cand = root / "Tesseract-OCR" / "tesseract.exe"
            if cand.is_file():
                return str(cand)
    if MACOS:
        cand = Path("/opt/homebrew/bin/tesseract")
        if cand.is_file():
            return str(cand)
    return None


# ---- summary used by the doctor and by error messages --------------------

def describe() -> dict[str, str | None]:
    """What was found, for the setup check and the log line at startup."""
    lib = find_ghostscript_lib()
    return {
        "ghostscript": find_ghostscript(),
        "ghostscript_lib": str(lib) if lib else None,
        "libreoffice": find_soffice(),
        "tesseract": find_tesseract(),
        "platform": sys.platform,
    }


def log_summary() -> None:
    info = describe()
    for key, value in info.items():
        if key == "platform":
            continue
        log.info("toolchain %-16s %s", key, value or "NOT FOUND")