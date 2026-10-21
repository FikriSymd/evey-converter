"""Runtime configuration for the evey-converter backend."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root: pdf-tool/
STATIC_DIR = BASE_DIR

# Working area lives outside the project so it is never served statically.
WORK_DIR = Path(os.environ.get("EVEY_WORK_DIR", Path.home() / ".evey" / "work"))
JOBS_DIR = WORK_DIR / "jobs"

# Job metadata database (SQLite). Never served; see db.py.
DB_PATH = Path(os.environ.get("EVEY_DB_PATH", WORK_DIR / "evey.db"))

# Upload limits (mirror the frontend values in app.js).
MAX_FILE_MB = 50
MAX_JOB_MB = 100
MAX_FILES_PER_JOB = 20

# Results are deleted for good one hour after the job finishes. The DB row
# goes with the files, so nothing about a finished job outlives its TTL.
TTL_SECONDS = int(os.environ.get("EVEY_TTL_SECONDS", 3600))
CLEANUP_INTERVAL = int(os.environ.get("EVEY_CLEANUP_INTERVAL", 300))

# 2 vCPU box: keep the pipeline shallow.
MAX_CONCURRENCY = 2

# Abuse guards. The per-IP limit is counted over a sliding window and keyed on
# a salted hash of the client IP, never the address itself (see ratelimit.py).
RATE_LIMIT_JOBS = int(os.environ.get("EVEY_RATE_LIMIT_JOBS", 60))
RATE_LIMIT_WINDOW = int(os.environ.get("EVEY_RATE_LIMIT_WINDOW", 3600))

# Total jobs allowed to sit queued or processing at once. Beyond this the box
# would only queue work it cannot finish, so new jobs are refused with 503.
MAX_QUEUE = int(os.environ.get("EVEY_MAX_QUEUE", 12))

# Secret used to hash client IPs. Generated on first run, never shipped.
IP_SALT_PATH = WORK_DIR / ".ip_salt"

# Subprocess timeout for a single conversion (seconds).
OP_TIMEOUT = 240

# Hard ceiling on how long one job may run, in-process work included. A file
# that cannot be processed in this window is abandoned rather than allowed to
# hold one of the two worker slots indefinitely.
JOB_TIMEOUT = int(os.environ.get("EVEY_JOB_TIMEOUT", 300))

# Refuse documents with more pages than this: a huge page count is how a small
# upload turns into minutes of CPU on a two-core box.
MAX_PAGES = int(os.environ.get("EVEY_MAX_PAGES", 500))

TESSERACT_LANGS = {"ind", "eng"}
