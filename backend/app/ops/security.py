"""Security operations: protect, unlock, watermark."""

from __future__ import annotations

from pathlib import Path

import pikepdf
import pymupdf

from ..config import MAX_PAGES
from ..util import OpError, guard_pages, safe_stem


def _guard(path: Path) -> None:
    """Refuse oversized documents before doing any real work on them."""
    try:
        with pymupdf.open(str(path)) as doc:
            guard_pages(doc, path.name, MAX_PAGES)
    except OpError:
        raise
    except Exception:
        # Not readable as a plain PDF (encrypted inputs land here); the tool
        # itself will produce the right error message.
        return


def protect(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    password = str(opts.get("password", ""))
    if not password:
        raise OpError("Password wajib diisi.")
    outputs: list[Path] = []
    for src in inputs:
        _guard(src)
        out = out_dir / f"{safe_stem(src.name)}-terkunci.pdf"
        try:
            with pikepdf.open(str(src)) as pdf:
                pdf.save(
                    str(out),
                    encryption=pikepdf.Encryption(owner=password, user=password, R=6),
                )
        except pikepdf.PasswordError as exc:
            raise OpError(f"'{src.name}' sudah terkunci, buka dulu.") from exc
        except Exception as exc:
            raise OpError(f"Gagal mengunci '{src.name}'.") from exc
        outputs.append(out)
    return outputs


def unlock(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    password = str(opts.get("password", ""))
    outputs: list[Path] = []
    for src in inputs:
        out = out_dir / f"{safe_stem(src.name)}-terbuka.pdf"
        try:
            with pikepdf.open(str(src), password=password) as pdf:
                pdf.save(str(out))
        except pikepdf.PasswordError as exc:
            raise OpError(f"Password salah untuk '{src.name}'.") from exc
        except Exception as exc:
            raise OpError(f"Gagal membuka '{src.name}'.") from exc
        outputs.append(out)
    return outputs


def watermark(inputs: list[Path], opts: dict, out_dir: Path) -> list[Path]:
    text = str(opts.get("text", "")).strip()
    if not text:
        raise OpError("Teks watermark kosong.")
    pos = str(opts.get("pos", "diagonal"))
    try:
        opacity = max(0.05, min(1.0, int(str(opts.get("opacity", "40"))) / 100))
    except ValueError:
        opacity = 0.4
    font = pymupdf.Font("helv")
    outputs: list[Path] = []
    for src in inputs:
        out = out_dir / f"{safe_stem(src.name)}-watermark.pdf"
        _guard(src)
        with pymupdf.open(str(src)) as doc:
            for page in doc:
                rect = page.rect
                size = max(18, min(rect.width, rect.height) / 12)
                width = font.text_length(text, fontsize=size)
                center = pymupdf.Point(rect.width / 2, rect.height / 2)
                # Anchor the baseline so the glyphs sit centred on the page.
                start = pymupdf.Point(center.x - width / 2, center.y + size * 0.35)
                morph = None
                if pos == "diagonal":
                    morph = (center, pymupdf.Matrix(45))
                page.insert_text(
                    start,
                    text,
                    fontsize=size,
                    fontname="helv",
                    color=(0.6, 0.18, 0.12),
                    fill_opacity=opacity,
                    morph=morph,
                )
            doc.save(str(out), garbage=4, deflate=True)
        outputs.append(out)
    return outputs
