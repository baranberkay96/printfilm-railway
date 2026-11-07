"""ASGI entry point for PRINTFILM on Railway (community template).

Serves upstream's FastAPI app (``app.main:app``, unmodified) with two template switches.

PRINTFILM_SIGNUP_ENABLED (default ``false``)
    Upstream lets anyone who can open the site register, and with billing off (upstream's default)
    every account generates on the operator's TokenFree key. Unless this is ``true``,
    ``POST /api/auth/register`` answers 403; the admin account comes from ADMIN_EMAIL /
    ADMIN_PASSWORD (railway/bootstrap.py). Turn it on to let people sign up, ideally together with
    billing (Admin -> System settings) so each account spends only the balance an admin grants.

PRINTFILM_PUBLIC_MEDIA_URLS (default ``true``)
    Seedance (video) fetches reference images and audio over public HTTPS. Upstream gets such URLs
    only from Aliyun OSS: without OSS, ``storage.republish_url`` returns the local ``/static/...``
    path, and image-to-video from uploaded images, asset-library pictures or provider links that
    have expired fails ("Seedance 需要公网可访问的图片 URL"). On Railway the Web service serves
    ``/static/`` over HTTPS, so while OSS is off and PUBLIC_BASE_URL is ``https://``, local media
    resolves to ``PUBLIC_BASE_URL/static/...`` instead. Upstream already maps such URLs back to the
    local file (``storage.local_path_from_url``). With OSS configured in the admin console,
    upstream's behaviour applies unchanged.
"""

from __future__ import annotations

import functools
import json
import os
import re
import sys
from typing import Any, Awaitable, Callable

Send = Callable[[dict], Awaitable[None]]
Receive = Callable[[], Awaitable[dict]]

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    if raw:
        print(
            f"[railway] warning: {name}={raw!r} is not true/false; using {str(default).lower()}",
            file=sys.stderr,
            flush=True,
        )
    return default


SIGNUP_ENABLED = _flag("PRINTFILM_SIGNUP_ENABLED", False)
PUBLIC_MEDIA_URLS = _flag("PRINTFILM_PUBLIC_MEDIA_URLS", True)

from app.config import get_settings  # noqa: E402  (after the flags: importing app.main configures logging)
from app.main import app as printfilm_app  # noqa: E402
from app.services import oss as _oss  # noqa: E402
from app.services import storage as _storage  # noqa: E402

# ── sign-up switch ───────────────────────────────────────────────────────────

_REGISTER_PATH = "/api/auth/register"
_SIGNUP_CLOSED = json.dumps(
    {
        "detail": "注册已关闭，请联系管理员开通账号。"
        "Sign-up is disabled on this server; ask the administrator for an account."
    },
    ensure_ascii=False,
).encode("utf-8")
_SLASHES = re.compile(r"/{2,}")


def _is_register(scope: dict[str, Any]) -> bool:
    if scope.get("type") != "http" or scope.get("method") != "POST":
        return False
    path = _SLASHES.sub("/", scope.get("path") or "")
    return path.rstrip("/") == _REGISTER_PATH


async def _signup_closed(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 403,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(_SIGNUP_CLOSED)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": _SIGNUP_CLOSED})


async def app(scope: dict[str, Any], receive: Receive, send: Send) -> None:
    """Upstream's app, with POST /api/auth/register closed unless sign-up is enabled."""
    if not SIGNUP_ENABLED and _is_register(scope):
        await _signup_closed(send)
        return
    await printfilm_app(scope, receive, send)


# ── public media URLs while OSS is off ──────────────────────────────────────

_upstream_republish_url = _storage.republish_url


def _public_url(url: str) -> str | None:
    """PUBLIC_BASE_URL/static/... for a local media file, or None."""
    base = (get_settings().public_base_url or "").strip().rstrip("/")
    if not base.startswith("https://"):
        return None
    local = _storage.local_path_from_url(url)
    if local is None or not local.is_file():
        return None
    try:
        rel = _storage.rel_static_url(local)
    except ValueError:  # outside /app/static
        return None
    return f"{base}{rel}"


@functools.wraps(_upstream_republish_url)
def republish_url(url: str | None, *, sync: bool = True) -> str | None:
    result = _upstream_republish_url(url, sync=sync)
    if not result or not PUBLIC_MEDIA_URLS:
        return result
    text = str(result)
    if text.startswith("https://") or _oss.oss_enabled() or not _storage.is_local_static_url(text):
        return result
    return _public_url(text) or result


_storage.republish_url = republish_url
