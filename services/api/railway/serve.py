"""Start PRINTFILM's API on Railway (community template).

Upstream runs ``uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1``. This keeps one
worker (the task runtime lives in the process) and changes only how it listens:

* the port comes from ``PORT`` (Railway's healthcheck probes it);
* one dual-stack socket on ``::`` (IPV6_V6ONLY off). A uvicorn ``--host ::`` socket would be
  IPv6-only and miss Railway's IPv4 healthcheck; ``0.0.0.0`` would miss IPv6-only private networks;
* proxy headers are trusted: only the Web and Admin services (Caddy) can reach the API;
* it waits a bounded time for Postgres and Redis, so a restart while they come up does not crash
  the startup (upstream turns Redis off for the life of the process after one failed connection).
"""

from __future__ import annotations

import os
import socket
import sys
import time
from urllib.parse import urlsplit

APP_DIR = "/app"
DEFAULT_PORT = 8000
LOG_LEVELS = frozenset({"critical", "error", "warning", "info", "debug", "trace"})


def log(message: str) -> None:
    print(f"[railway] {message}", file=sys.stderr, flush=True)


def listen_port() -> int:
    raw = os.environ.get("PORT", "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        port = int(raw)
    except ValueError:
        port = 0
    if not 1 <= port <= 65535:
        log(f"warning: PORT={raw!r} is not a TCP port; using {DEFAULT_PORT}")
        return DEFAULT_PORT
    return port


def bind_socket(port: int) -> socket.socket:
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(("::", port))
        return sock
    except OSError as exc:
        log(f"warning: no dual-stack socket ({exc}); listening on 0.0.0.0:{port} (IPv4 only)")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    return sock


def endpoint(url: str, default_port: int) -> tuple[str, int] | None:
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError:
        return None
    if not host:
        return None
    return host, port or default_port


def wait_for(name: str, target: tuple[str, int] | None, limit: int) -> None:
    if target is None:
        return
    host, port = target
    waited = 0
    while True:
        try:
            with socket.create_connection((host, port), timeout=5):
                return
        except OSError as exc:
            if waited >= limit:
                log(f"warning: {name} at {host}:{port} still unreachable after {limit}s ({exc}); starting anyway")
                return
            if waited % 30 == 0:
                log(f"waiting for {name} at {host}:{port} ({waited}s)")
        time.sleep(5)
        waited += 5


def main() -> None:
    sys.path.insert(0, APP_DIR)
    os.chdir(APP_DIR)
    try:
        limit = max(0, int(os.environ.get("TEMPLATE_WAIT_SECONDS", "180")))
    except ValueError:
        limit = 180
    wait_for("Postgres", endpoint(os.environ.get("DATABASE_URL", ""), 5432), limit)
    wait_for("Redis", endpoint(os.environ.get("REDIS_URL", ""), 6379), limit)

    import uvicorn

    log_level = os.environ.get("UVICORN_LOG_LEVEL", "info").strip().lower()
    if log_level not in LOG_LEVELS:
        log(f"warning: UVICORN_LOG_LEVEL={log_level!r} is unknown; using info")
        log_level = "info"
    port = listen_port()
    sock = bind_socket(port)
    config = uvicorn.Config(
        "railway_app:app",
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_graceful_shutdown=20,
        log_level=log_level,
    )
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
