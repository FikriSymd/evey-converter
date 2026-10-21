"""Abuse guards: per-client rate limit and a global queue cap.

Two different problems, two different checks:

- **Per client**: a sliding window over the job ledger. The client is
  identified by a salted HMAC of its IP, never the address itself, so the
  database cannot be turned into a log of who visited. The salt lives in a
  local file (mode 600) and is generated on first run.
- **Global queue**: how many jobs are queued or running right now. Past the
  cap the box can only accumulate work it will not finish, so the request is
  refused with 503 rather than accepted and starved.

Everything is best-effort by design: if the ledger read fails, the request is
allowed rather than blocked. A broken rate limiter must never take the site
down.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import stat
import time

from . import config, db

log = logging.getLogger("evey.ratelimit")

_salt: bytes | None = None


def _load_salt() -> bytes:
    """Read the HMAC salt, creating it on first run with owner-only perms."""
    global _salt
    if _salt is not None:
        return _salt
    path = config.IP_SALT_PATH
    try:
        if path.exists():
            _salt = path.read_bytes()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            _salt = secrets.token_bytes(32)
            path.write_bytes(_salt)
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            log.info("generated IP hash salt at %s", path)
    except OSError:
        # Unwritable location: fall back to an in-process salt. Limits still
        # hold for the life of the process; they just do not survive a restart.
        log.warning("could not persist IP salt; using a session-only salt")
        _salt = secrets.token_bytes(32)
    return _salt


def hash_ip(ip: str) -> str:
    """Salted, non-reversible client key. Never store the raw address."""
    return hmac.new(_load_salt(), ip.encode("utf-8"), hashlib.sha256).hexdigest()


def client_ip(request) -> str:
    """The real client address behind the Cloudflare tunnel.

    Through cloudflared, ``request.client.host`` is always the loopback
    address, so the forwarded header is the only useful signal. Anything that
    is not a parsed address is folded to a single bucket rather than trusted.
    """
    for header in ("cf-connecting-ip", "x-forwarded-for", "x-real-ip"):
        value = request.headers.get(header)
        if value:
            first = value.split(",")[0].strip()
            if first:
                return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RateLimited(Exception):
    """The caller has spent its allowance for the current window."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = max(1, retry_after)
        super().__init__("rate limit reached")


def check(request) -> None:
    """Raise RateLimited when this client is out of allowance."""
    now = time.time()
    since = now - config.RATE_LIMIT_WINDOW
    key = hash_ip(client_ip(request))
    try:
        used = db.count_hits(key, since)
    except Exception:  # noqa: BLE001 - never fail the request on a limiter bug
        log.exception("rate-limit read failed; allowing request")
        return
    if used >= config.RATE_LIMIT_JOBS:
        # Tell the client when the window actually frees up: when its oldest
        # counted request ages out, not the full window from now.
        oldest = db.oldest_hit(key, since)
        retry = config.RATE_LIMIT_WINDOW - int(now - (oldest or since))
        log.info("rate limit hit for %s (%d/%d)", key[:12], used, config.RATE_LIMIT_JOBS)
        raise RateLimited(max(retry, 1))


def record(request) -> None:
    """Count an accepted job against the client."""
    try:
        db.record_hit(hash_ip(client_ip(request)), time.time())
    except Exception:  # noqa: BLE001
        log.exception("rate-limit write failed; request already accepted")


def queue_depth() -> int:
    try:
        return db.count_active()
    except Exception:  # noqa: BLE001
        log.exception("queue-depth read failed; treating as empty")
        return 0


def has_capacity() -> bool:
    return queue_depth() < config.MAX_QUEUE


def prune() -> int:
    """Drop ledger rows past the window, so hashes do not outlive their use."""
    try:
        return db.prune_hits(time.time() - config.RATE_LIMIT_WINDOW)
    except Exception:  # noqa: BLE001
        log.exception("rate-limit prune failed")
        return 0