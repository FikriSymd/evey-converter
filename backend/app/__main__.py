"""Entrypoint: `python -m app.main` or uvicorn app.main:app."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8080,
        log_level="info",
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
