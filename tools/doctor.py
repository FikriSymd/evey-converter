"""Setup check: say exactly what is ready and what is missing.

Run it with the project virtualenv, from anywhere:

    .venv\\Scripts\\python.exe tools\\doctor.py        (Windows)
    .venv/bin/python tools/doctor.py                   (Linux, macOS)

It prints one line per dependency, then a short verdict. Exit code is 0 when
every required program is present, 1 otherwise, so a script can check it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"


def mark(ok: bool) -> str:
    return f"{GREEN}OK  {RESET}" if ok else f"{RED}HILANG{RESET}"


def main() -> int:
    from app import toolchain

    print()
    print("Pemeriksaan evey-converter")
    print("=" * 60)

    failures: list[str] = []

    # --- program pendukung -------------------------------------------------
    info = toolchain.describe()
    checks = [
        ("Python", True, f"{sys.version.split()[0]}", "semua tool"),
        ("Ghostscript", info["ghostscript"] is not None, info["ghostscript"] or "",
         "Kompres, PDF/A, Perbaiki"),
        ("Ghostscript lib", info["ghostscript_lib"] is not None, info["ghostscript_lib"] or "",
         "label PDF/A"),
        ("LibreOffice", info["libreoffice"] is not None, info["libreoffice"] or "",
         "Word/Excel/PowerPoint ke PDF"),
        ("Tesseract", info["tesseract"] is not None, info["tesseract"] or "",
         "OCR"),
    ]
    for name, ok, detail, needed in checks:
        print(f"  [{mark(ok)}] {name:<16} {needed}")
        if detail:
            print(f"            {DIM}{detail}{RESET}")
        if not ok and name != "Ghostscript lib":
            failures.append(name)

    # --- paket Python ------------------------------------------------------
    print()
    print("Paket Python")
    print("-" * 60)
    packages = [
        ("fastapi", "API"),
        ("uvicorn", "server"),
        ("multipart", "unggah file"),
        ("pymupdf", "baca/tulis PDF"),
        ("pikepdf", "kunci/buka PDF"),
        ("pdf2docx", "PDF ke Word"),
        ("docx", "tulis Word"),
        ("pptx", "tulis PowerPoint"),
        ("openpyxl", "tulis Excel"),
        ("pdfplumber", "baca tabel"),
        ("PIL", "gambar"),
        ("weasyprint", "Web ke PDF"),
        ("ocrmypdf", "OCR"),
    ]
    for module, purpose in packages:
        try:
            __import__(module)
            print(f"  [{GREEN}OK  {RESET}] {module:<14} {DIM}{purpose}{RESET}")
        except Exception as exc:  # noqa: BLE001 - report, do not crash
            print(f"  [{RED}HILANG{RESET}] {module:<14} {purpose}  ({type(exc).__name__})")
            failures.append(f"paket {module}")

    # --- weasyprint benar benar bisa render (butuh GTK di Windows) --------
    print()
    print("Uji nyata WeasyPrint (butuh GTK di Windows)")
    print("-" * 60)
    try:
        import logging

        import weasyprint  # noqa: F401
        from weasyprint import HTML

        # WeasyPrint logs every layout step at INFO; silence it for this check.
        logging.getLogger("weasyprint").setLevel(logging.ERROR)
        logging.getLogger("fontTools").setLevel(logging.ERROR)
        out = "/dev/null" if sys.platform != "win32" else "NUL"
        HTML(string="<p>tes</p>").write_pdf(out)
        print(f"  [{GREEN}OK  {RESET}] render HTML ke PDF berhasil")
    except Exception as exc:  # noqa: BLE001
        print(f"  [{RED}GAGAL{RESET}] {type(exc).__name__}: {exc}")
        print(f"            {DIM}Di Windows ini biasanya GTK belum terpasang "
              f"atau WEASYPRINT_DLL_DIRECTORIES salah.{RESET}")
        failures.append("WeasyPrint")

    # --- berkas penting ----------------------------------------------------
    print()
    print("Berkas proyek")
    print("-" * 60)
    for rel in ("index.html", "app.js", "styles.css", "backend/requirements.txt"):
        p = ROOT / rel
        print(f"  [{mark(p.is_file())}] {rel}")
        if not p.is_file():
            failures.append(rel)

    # --- kesimpulan --------------------------------------------------------
    print()
    print("=" * 60)
    if failures:
        print(f"{RED}Ada {len(failures)} hal yang belum siap:{RESET}")
        for f in failures:
            print(f"  - {f}")
        print()
        print("Buka panduan setup, bagian troubleshooting, buat langkah perbaikannya.")
        return 1
    print(f"{GREEN}Semua siap. Jalankan aplikasinya, lalu buka http://127.0.0.1:8080{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
