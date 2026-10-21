"""FastAPI application: job API + the static frontend.

Only the frontend files are served by name; the backend source is never
reachable over HTTP.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from . import config, db, ratelimit, registry, toolchain
from .jobs import JobManager
from .util import OpError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("evey")

app = FastAPI(title="evey-converter", docs_url=None, redoc_url=None)
manager = JobManager()
toolchain.log_summary()

# Frontend files that may be served, by name. Everything else is 404.
STATIC_FILES = {"index.html", "styles.css", "app.js", "favicon.ico"}
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".ico": "image/x-icon",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
}

_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_upload_name(name: str) -> str:
    name = Path(name or "file").name
    return _FILENAME_SAFE.sub("-", name) or "file"


def _serve(name: str) -> FileResponse:
    if name not in STATIC_FILES:
        raise HTTPException(status_code=404, detail="Tidak ditemukan.")
    path = config.STATIC_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Tidak ditemukan.")
    return FileResponse(path, media_type=STATIC_TYPES.get(path.suffix, "application/octet-stream"))


@app.get("/")
def index() -> FileResponse:
    return _serve("index.html")


@app.get("/{name}")
def static_file(name: str) -> FileResponse:
    return _serve(name)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "tools": len(registry.TOOLS),
        "jobs": len(db.all_rows()),
        "queue": ratelimit.queue_depth(),
        "queue_max": config.MAX_QUEUE,
    }


@app.get("/api/doctor")
def doctor() -> dict:
    """Report the external programs each group of tools depends on.

    A fresh machine usually has Python and nothing else, in which case half the
    catalogue cannot run. This endpoint says which half, and what to install,
    instead of leaving the user with a bare error on the first attempt.
    """
    found = toolchain.describe()
    gs = found["ghostscript"] is not None
    lo = found["libreoffice"] is not None
    tess = found["tesseract"] is not None

    checks = [
        {"name": "Python", "found": True, "needed_by": "semua tool"},
        {"name": "Ghostscript", "found": gs, "needed_by": "Kompres, PDF/A, Perbaiki"},
        {"name": "LibreOffice", "found": lo, "needed_by": "Word/Excel/PowerPoint ke PDF"},
        {"name": "Tesseract", "found": tess, "needed_by": "OCR"},
    ]
    missing = [c["name"] for c in checks if not c["found"]]
    return {
        "ok": not missing,
        "platform": found["platform"],
        "checks": checks,
        "missing": missing,
        "paths": {
            "ghostscript": found["ghostscript"],
            "ghostscript_lib": found["ghostscript_lib"],
            "libreoffice": found["libreoffice"],
            "tesseract": found["tesseract"],
        },
    }


@app.get("/api/tools")
def tools() -> dict:
    return {
        "tools": [
            {"id": t.id, "kind": t.kind, "multiple": t.multiple}
            for t in registry.TOOLS.values()
        ]
    }


@app.post("/api/jobs")
async def create_job(
    request: Request,
    tool: str = Form(...),
    options: str = Form("{}"),
    files: list[UploadFile] = File(...),
) -> JSONResponse:
    try:
        spec = registry.get(tool)
    except OpError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Abuse guards run before any file is read off the wire.
    try:
        ratelimit.check(request)
    except ratelimit.RateLimited as exc:
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak permintaan. Coba lagi sebentar lagi.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    if not ratelimit.has_capacity():
        raise HTTPException(
            status_code=503,
            detail="Server lagi penuh. Coba lagi sebentar lagi.",
            headers={"Retry-After": "60"},
        )

    if not files:
        raise HTTPException(status_code=400, detail="Tidak ada file yang diunggah.")
    if len(files) > config.MAX_FILES_PER_JOB:
        raise HTTPException(
            status_code=400,
            detail=f"Maksimal {config.MAX_FILES_PER_JOB} file per pekerjaan.",
        )
    if not spec.multiple and len(files) > 1:
        raise HTTPException(
            status_code=400,
            detail="Tool ini hanya menerima satu file.",
        )

    try:
        parsed = json.loads(options) if options else {}
        if not isinstance(parsed, dict):
            parsed = {}
    except json.JSONDecodeError:
        parsed = {}

    tmp_root = Path(tempfile.mkdtemp(prefix="evey-up-"))
    staged: list[tuple[str, Path]] = []
    total = 0
    try:
        for i, upload in enumerate(files):
            data = await upload.read()
            size = len(data)
            if size == 0:
                raise HTTPException(status_code=400, detail="Ada file kosong.")
            if size > config.MAX_FILE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{upload.filename}' lebih dari {config.MAX_FILE_MB}MB.",
                )
            total += size
            if total > config.MAX_JOB_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=f"Total file lebih dari {config.MAX_JOB_MB}MB.",
                )
            safe = f"{i:03d}-{_safe_upload_name(upload.filename or 'file')}"
            dest = tmp_root / safe
            dest.write_bytes(data)
            staged.append((safe, dest))

        job = manager.create(tool, parsed, staged)
        ratelimit.record(request)
        return JSONResponse(job.public(), status_code=202)
    finally:
        shutil_rmtree(tmp_root)


def shutil_rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Pekerjaan tidak ditemukan.")
    if job.expires_at <= time.time():
        raise HTTPException(status_code=410, detail="File sudah dihapus otomatis 1 jam yang lalu.")
    return job.public()


@app.get("/api/jobs/{job_id}/download")
def job_download(job_id: str):
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Pekerjaan tidak ditemukan.")
    if job.expires_at <= time.time():
        raise HTTPException(status_code=410, detail="File sudah dihapus otomatis 1 jam yang lalu.")
    if job.status == "error":
        raise HTTPException(status_code=422, detail=job.error or "Pemrosesan gagal.")
    if job.status != "done":
        raise HTTPException(status_code=409, detail="Pekerjaan belum selesai.")
    path = manager.result_path(job)
    if path is None:
        raise HTTPException(status_code=404, detail="File hasil tidak ada.")
    return FileResponse(path, filename=path.name)
