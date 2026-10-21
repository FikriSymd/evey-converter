"""Job store, worker queue, and TTL cleanup, backed by SQLite.

Job metadata lives in the database (db.py); the files live under
JOBS_DIR/<job_id>/. Both are removed the moment the job's TTL passes, so a
finished job leaves nothing behind: no row, no file.

`expires_at` is the single source of truth for the one hour rule. It is set
when the job ends and checked in three places: the sweeper deletes rows and
folders, and the API refuses to serve a job whose deadline has passed even if
the sweeper has not run yet.
"""

from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, db, progress, ratelimit, registry
from .util import OpError

log = logging.getLogger("evey.jobs")


class Job:
    """A job as read back from the database."""

    def __init__(self, row) -> None:
        self.id: str = row["id"]
        self.tool: str = row["tool"]
        self.status: str = row["status"]
        self.error: str = row["error"]
        self.created: float = row["created"]
        self.finished: float = row["finished"]
        self.expires_at: float = row["expires_at"]
        self._outputs_raw: str = row["outputs"]

    @property
    def dir(self) -> Path:
        return config.JOBS_DIR / self.id

    def outputs(self) -> list[Path]:
        return [self.dir / "out" / name for name in json.loads(self._outputs_raw or "[]")]

    def public(self) -> dict:
        files = [
            {"name": p.name, "size": p.stat().st_size if p.exists() else 0}
            for p in self.outputs()
        ]
        return {
            "id": self.id,
            "tool": self.tool,
            "status": self.status,
            "error": self.error,
            "expires_in": max(0, int(self.expires_at - time.time())),
            "progress": progress.read(self.dir / "progress.json"),
            "files": files,
            "downloads": [f"/api/jobs/{self.id}/download"] if files else [],
        }


def _row_to_job(row) -> Job:
    return Job(row)


class JobManager:
    def __init__(self) -> None:
        self._pool = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENCY)
        config.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        db.init()
        self._sweep_orphans()
        self._stop = threading.Event()
        self._sweeper = threading.Thread(target=self._sweep_loop, daemon=True)
        self._sweeper.start()

    # ---- public API ---------------------------------------------------
    def create(self, tool_id: str, options: dict, uploads: list[tuple[str, Path]]) -> Job:
        job_id = uuid.uuid4().hex
        job_dir = config.JOBS_DIR / job_id
        in_dir = job_dir / "in"
        out_dir = job_dir / "out"
        in_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        names: list[str] = []
        for original, tmp_path in uploads:
            dest = in_dir / original
            shutil.move(str(tmp_path), str(dest))
            names.append(original)

        now = time.time()
        db.insert(
            {
                "id": job_id,
                "tool": tool_id,
                "status": "queued",
                "error": "",
                "options": options,
                "inputs": names,
                "outputs": [],
                "created": now,
                # Provisional deadline: covers a job that never finishes.
                "finished": 0.0,
                "expires_at": now + config.TTL_SECONDS,
            }
        )
        self._pool.submit(self._run, job_id, tool_id, options, in_dir, out_dir)
        return self.get(job_id)

    def get(self, job_id: str) -> Job | None:
        for row in db.all_rows():
            if row["id"] == job_id:
                return _row_to_job(row)
        return None

    def result_path(self, job: Job) -> Path | None:
        """The single file to hand back: the lone output, or a zip of many."""
        outputs = [p for p in job.outputs() if p.exists()]
        if not outputs:
            return None
        if len(outputs) == 1:
            return outputs[0]
        zip_path = job.dir / "out" / f"{job.tool}-hasil.zip"
        if not zip_path.exists():
            from .util import zip_outputs

            zip_outputs(outputs, zip_path)
        return zip_path

    # ---- internals ----------------------------------------------------
    def _run(self, job_id: str, tool_id: str, options: dict, in_dir: Path, out_dir: Path) -> None:
        db.update(job_id, status="processing")
        # Progress for this job is reported into its own directory, so it is
        # deleted by the same sweep that removes the job.
        progress_path = config.JOBS_DIR / job_id / "progress.json"
        progress.bind(progress_path)
        # A handler stuck in pure Python ignores the subprocess timeout; this
        # watchdog is the only thing that frees the worker slot.
        done = threading.Event()
        watchdog = threading.Thread(target=self._watch, args=(job_id, done), daemon=True)
        watchdog.start()
        try:
            tool = registry.get(tool_id)
            inputs = sorted(p for p in in_dir.iterdir() if p.is_file())
            produced = tool.handler(inputs, options, out_dir)
            if not produced:
                raise OpError("Proses selesai tapi tidak ada file hasil.")
            # A job the watchdog already failed stays failed: a late result
            # must not resurrect a deadline the caller was told about.
            row = db.get(job_id)
            if row is None or row["status"] != "processing":
                log.info("job %s finished after being failed; keeping error", job_id)
                return
            db.update(
                job_id,
                status="done",
                error="",
                outputs=[p.name for p in produced],
                finished=time.time(),
                # The one hour clock starts when the work ends.
                expires_at=time.time() + config.TTL_SECONDS,
            )
        except OpError as exc:
            self._fail(job_id, str(exc))
        except Exception as exc:  # noqa: BLE001 - report, do not crash the worker
            log.exception("job %s failed", job_id)
            self._fail(job_id, f"Gagal memproses file: {exc}")
        finally:
            done.set()
            progress.unbind()

    def _fail(self, job_id: str, message: str) -> None:
        now = time.time()
        db.update(
            job_id,
            status="error",
            error=message,
            finished=now,
            expires_at=now + config.TTL_SECONDS,
        )

    def _watch(self, job_id: str, done: threading.Event) -> None:
        """Fail a job that has outrun the per-job deadline.

        This is honest about its own limit: Python cannot preempt a thread, so
        CPU-bound work inside a handler keeps running. What the watchdog does
        is stop the client from waiting on a job that will never answer, and
        mark it so the sweeper collects it at TTL. :meth:`_run` refuses to
        overwrite that verdict if the handler finishes later.
        """
        if done.wait(config.JOB_TIMEOUT):
            return
        row = db.get(job_id)
        if row is None or row["status"] != "processing":
            return
        log.warning("job %s exceeded %ss; marking failed", job_id, config.JOB_TIMEOUT)
        self._fail(job_id, "Proses terlalu lama dan dihentikan.")

    def _sweep_orphans(self) -> None:
        """Startup: drop rows that died, and folders with no live row.

        Without this, a restart would leave job folders on disk forever: the
        old in-memory registry was empty, so nothing knew to delete them.
        """
        now = time.time()
        for job_id in db.expired_ids(now):
            shutil.rmtree(config.JOBS_DIR / job_id, ignore_errors=True)
            log.info("startup sweep removed expired job %s", job_id)
        db.delete(db.expired_ids(now))

        known = {row["id"] for row in db.all_rows()}
        for entry in config.JOBS_DIR.iterdir():
            if entry.is_dir() and entry.name not in known:
                shutil.rmtree(entry, ignore_errors=True)
                log.info("startup sweep removed orphan folder %s", entry.name)

    def _sweep_loop(self) -> None:
        while not self._stop.wait(config.CLEANUP_INTERVAL):
            now = time.time()
            expired = db.expired_ids(now)
            for job_id in expired:
                shutil.rmtree(config.JOBS_DIR / job_id, ignore_errors=True)
            if expired:
                db.delete(expired)
                log.info("swept %d job(s)", len(expired))
            # Ledger rows are dropped with the same clock: a client hash stops
            # existing once its window has passed.
            pruned = ratelimit.prune()
            if pruned:
                log.info("pruned %d rate-limit hit(s)", pruned)