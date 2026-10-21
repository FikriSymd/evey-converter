"""End-to-end API test: POST every tool to a running server and download.

Usage:  python tests/test_api.py [base_url]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
FIX = Path("/tmp/evey-fixtures")
PDF = FIX / "laporan.pdf"
PDF2 = FIX / "lampiran.pdf"

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


def multipart(fields: dict, files: list[Path]) -> tuple[bytes, str]:
    boundary = "----evey" + str(int(time.time() * 1000))
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    for path in files:
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
                f'filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
            ).encode()
        )
        parts.append(path.read_bytes())
        parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def post(tool: str, files: list[Path], opts: dict) -> dict:
    body, ctype = multipart({"tool": tool, "options": json.dumps(opts)}, files)
    req = urllib.request.Request(f"{BASE}/api/jobs", data=body, headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())


def wait(job_id: str, timeout: float = 300) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with urllib.request.urlopen(f"{BASE}/api/jobs/{job_id}", timeout=30) as resp:
            data = json.loads(resp.read())
        if data["status"] in ("done", "error"):
            return data
        time.sleep(0.4)
    raise TimeoutError(job_id)


def ensure_locked() -> None:
    """unlock needs an encrypted input; build it if the fixture is missing."""
    locked = FIX / "_locked.pdf"
    if locked.exists():
        return
    import pikepdf

    with pikepdf.open(str(PDF)) as src:
        src.save(str(locked), encryption=pikepdf.Encryption(owner="rahasia123", user="rahasia123", R=6))


def main() -> int:
    ensure_locked()
    ok, fail = [], []
    for tool, (files, opts) in CASES.items():
        start = time.time()
        try:
            job = post(tool, files, opts)
            final = wait(job["id"])
            if final["status"] != "done":
                raise RuntimeError(final["error"] or "status " + final["status"])
            url = f"{BASE}/api/jobs/{final['id']}/download"
            with urllib.request.urlopen(url, timeout=120) as resp:
                blob = resp.read()
            if not blob:
                raise RuntimeError("empty download")
            elapsed = time.time() - start
            names = ", ".join(f["name"] for f in final["files"][:3])
            print(f"PASS {tool:14} {elapsed:5.1f}s  {len(blob):>7}b  {names}")
            ok.append(tool)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {tool:14} {type(exc).__name__}: {exc}")
            fail.append(tool)

    print(f"\n{len(ok)}/{len(CASES)} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
