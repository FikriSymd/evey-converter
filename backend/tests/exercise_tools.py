"""Exercise every tool in the registry against the sample fixtures.

Run from backend/:  python tests/exercise_tools.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import registry  # noqa: E402
from app.util import OpError  # noqa: E402

FIX = Path("/tmp/evey-fixtures")
PDF = FIX / "laporan.pdf"
PDF2 = FIX / "lampiran.pdf"

# tool -> (inputs, options)
CASES = {
    "merge": ([PDF, PDF2], {}),
    "split": ([PDF], {"mode": "range", "range": "1-2"}),
    "organize": ([PDF], {"order": "3,1,2"}),
    "rotate": ([PDF], {"angle": "90", "scope": "all"}),
    "remove_pages": ([PDF], {"range": "2"}),
    "extract_pages": ([PDF], {"range": "1,3"}),
    "compress": ([PDF], {"level": "rec"}),
    "repair": ([PDF], {}),
    "pdfa": ([PDF], {}),
    "pdf_word": ([PDF], {}),
    "pdf_excel": ([PDF], {}),
    "pdf_ppt": ([PDF], {}),
    "word_pdf": ([FIX / "dokumen.docx"], {}),
    "excel_pdf": ([FIX / "tabel.xlsx"], {}),
    "ppt_pdf": ([FIX / "presentasi.pptx"], {}),
    "pdf_jpg": ([PDF], {"imgfmt": "jpg", "dpi": "96"}),
    "jpg_pdf": ([FIX / "gambar1.png", FIX / "gambar2.png"], {}),
    "html_pdf": ([FIX / "halaman.html"], {}),
    "ocr": ([PDF], {"lang": "ind"}),
    "protect": ([PDF], {"password": "rahasia123"}),
    "unlock": ([FIX / "_locked.pdf"], {"password": "rahasia123"}),
    "watermark": ([PDF], {"text": "RAHASIA", "pos": "diagonal", "opacity": "40"}),
}

# unlock needs a locked input, built first.
import pikepdf  # noqa: E402

locked = FIX / "_locked.pdf"
with pikepdf.open(str(PDF)) as src:
    src.save(str(locked), encryption=pikepdf.Encryption(owner="rahasia123", user="rahasia123", R=6))


def main() -> int:
    ok, fail = [], []
    for tool_id, (inputs, opts) in CASES.items():
        tool = registry.get(tool_id)
        out_dir = Path(tempfile.mkdtemp(prefix=f"evey-{tool_id}-"))
        start = time.time()
        try:
            produced = tool.handler(list(inputs), opts, out_dir)
            produced = [p for p in produced if p.exists() and p.stat().st_size > 0]
            if not produced:
                raise OpError("tidak ada output")
            elapsed = time.time() - start
            sizes = ", ".join(f"{p.name}({p.stat().st_size}b)" for p in produced[:3])
            more = "" if len(produced) <= 3 else f" +{len(produced) - 3}"
            ok.append(tool_id)
            print(f"PASS {tool_id:14} {elapsed:5.1f}s  {sizes}{more}")
        except Exception as exc:  # noqa: BLE001
            fail.append((tool_id, exc))
            print(f"FAIL {tool_id:14} {type(exc).__name__}: {exc}")
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    print(f"\n{len(ok)}/{len(CASES)} passed")
    if fail:
        print("failures:", ", ".join(t for t, _ in fail))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
