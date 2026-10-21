"""SQLite persistence for job metadata.

The database lives outside the project (config.DB_PATH under WORK_DIR) and is
never served over HTTP. It stores job metadata only: tool, status, timestamps.
Uploaded files and results stay on disk under JOBS_DIR and are deleted, with
the job row, the moment the TTL passes. No file content ever reaches the DB,
so the privacy promise ("nothing is kept") still holds.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id         TEXT PRIMARY KEY,
  tool       TEXT NOT NULL,
  status     TEXT NOT NULL,
  error      TEXT NOT NULL DEFAULT '',
  options    TEXT NOT NULL DEFAULT '{}',
  inputs     TEXT NOT NULL DEFAULT '[]',
  outputs    TEXT NOT NULL DEFAULT '[]',
  created    REAL NOT NULL,
  finished   REAL NOT NULL DEFAULT 0,
  expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_expires ON jobs(expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Rate-limit ledger. `ip_hash` is a salted HMAC of the client address, never
-- the address itself; rows are deleted once the counting window passes.
CREATE TABLE IF NOT EXISTS rate_hits (
  ip_hash TEXT NOT NULL,
  ts      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_hash_ts ON rate_hits(ip_hash, ts);
"""


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        # WAL keeps the sweeper from blocking reads on this 2 vCPU box.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        yield conn
    finally:
        conn.close()


def init() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def insert(row: dict) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO jobs
               (id, tool, status, error, options, inputs, outputs, created, finished, expires_at)
               VALUES (:id, :tool, :status, :error, :options, :inputs, :outputs,
                       :created, :finished, :expires_at)""",
            {
                **row,
                "options": json.dumps(row.get("options", {})),
                "inputs": json.dumps(row.get("inputs", [])),
                "outputs": json.dumps(row.get("outputs", [])),
            },
        )


def update(job_id: str, **fields) -> None:
    if not fields:
        return
    for key in ("options", "inputs", "outputs"):
        if key in fields:
            fields[key] = json.dumps(fields[key])
    cols = ", ".join(f"{k} = :{k}" for k in fields)
    with connect() as c:
        c.execute(f"UPDATE jobs SET {cols} WHERE id = :id", {**fields, "id": job_id})


def all_rows() -> list[sqlite3.Row]:
    with connect() as c:
        return list(c.execute("SELECT * FROM jobs"))


def get(job_id: str) -> sqlite3.Row | None:
    with connect() as c:
        return c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def expired_ids(now: float) -> list[str]:
    with connect() as c:
        return [r["id"] for r in c.execute("SELECT id FROM jobs WHERE expires_at <= ?", (now,))]


def count_active() -> int:
    """Jobs still queued or being processed: the live queue depth."""
    with connect() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM jobs WHERE status IN ('queued', 'processing')"
        ).fetchone()
        return int(row["n"])


# ---- rate-limit ledger --------------------------------------------------

def record_hit(ip_hash: str, now: float) -> None:
    with connect() as c:
        c.execute("INSERT INTO rate_hits (ip_hash, ts) VALUES (?, ?)", (ip_hash, now))


def count_hits(ip_hash: str, since: float) -> int:
    with connect() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM rate_hits WHERE ip_hash = ? AND ts >= ?",
            (ip_hash, since),
        ).fetchone()
        return int(row["n"])


def oldest_hit(ip_hash: str, since: float) -> float | None:
    """Timestamp of the earliest hit in the window, for a real Retry-After."""
    with connect() as c:
        row = c.execute(
            "SELECT MIN(ts) AS ts FROM rate_hits WHERE ip_hash = ? AND ts >= ?",
            (ip_hash, since),
        ).fetchone()
        return row["ts"] if row and row["ts"] is not None else None


def prune_hits(before: float) -> int:
    """Drop ledger rows older than a window; the hash stops existing there."""
    with connect() as c:
        return c.execute("DELETE FROM rate_hits WHERE ts < ?", (before,)).rowcount


def delete(ids: list[str]) -> None:
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    with connect() as c:
        c.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", ids)
