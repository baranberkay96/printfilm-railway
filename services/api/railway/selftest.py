"""Build-time self-test for PRINTFILM on Railway (community template); run by the API Dockerfile.

Fails the image build when an upstream name or behaviour this template relies on has changed:
the sign-up switch and the public-media-URL hook in railway_app.py, and the functions
bootstrap.py calls. Needs neither a database nor network access.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
import sys

sys.path.insert(0, "/app")
os.environ["PUBLIC_BASE_URL"] = "https://selftest.invalid"
os.environ["PRINTFILM_SIGNUP_ENABLED"] = "false"
os.environ["PRINTFILM_PUBLIC_MEDIA_URLS"] = "true"
os.environ.pop("OSS_ENABLED", None)


def check(ok: bool, what: str) -> None:
    if not ok:
        print(f"[selftest] FAILED: {what}", file=sys.stderr, flush=True)
        sys.exit(1)


async def status_of(asgi_app, method: str, path: str) -> int:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"selftest"), (b"content-type", b"application/json")],
        "client": ("127.0.0.1", 40000),
        "server": ("selftest", 8000),
    }
    sent: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    await asgi_app(scope, receive, send)
    starts = [m for m in sent if m.get("type") == "http.response.start"]
    return int(starts[0]["status"]) if starts else -1


def main() -> None:
    import railway_app
    from app.services import storage

    # Every caller must look republish_url up on the module, or the hook would not reach it.
    check(storage.republish_url is railway_app.republish_url, "storage.republish_url is patched")
    pattern = re.compile(r"from\s+app\.services\.storage\s+import[^\n]*\brepublish_url\b")
    for path in pathlib.Path("/app/app").rglob("*.py"):
        check(not pattern.search(path.read_text(encoding="utf-8")), f"{path} imports republish_url by name")

    probe = storage.GENERATED_ROOT / "railway-selftest.png"
    probe.write_bytes(b"selftest")
    try:
        public = storage.republish_url("/static/generated/railway-selftest.png", sync=True)
        check(public == "https://selftest.invalid/static/generated/railway-selftest.png", f"public URL, got {public!r}")
        check(storage.local_path_from_url(public) == probe, "public URL maps back to the local file")
        check(storage.is_local_static_url(public), "public URL counts as local media")
        missing = storage.republish_url("/static/generated/railway-missing.png", sync=True)
        check(missing == "/static/generated/railway-missing.png", f"missing file stays local, got {missing!r}")
        check(storage.republish_url("https://cdn.example.com/a.png") == "https://cdn.example.com/a.png", "remote URL unchanged")
        check(storage.republish_url(None) is None, "None unchanged")
    finally:
        probe.unlink()

    check(asyncio.run(status_of(railway_app.app, "POST", "/api/auth/register")) == 403, "sign-up closed")
    check(asyncio.run(status_of(railway_app.app, "POST", "//api/auth/register/")) == 403, "sign-up closed (slashes)")
    check(asyncio.run(status_of(railway_app.app, "GET", "/api/railway-selftest-missing")) == 404, "other paths reach upstream")

    # Names bootstrap.py uses.
    from app.database import AsyncSessionLocal, dispose_engine, engine, init_db  # noqa: F401
    from app.main import _apply_schema_patches  # noqa: F401
    from app.models import User
    from app.models_settings import SystemModelChannelRow
    from app.services.auth import hash_password, verify_password
    from app.services.model_settings import _decrypt_secret, _encrypt_secret
    from app.services.tokenfree_gateway import TOKENFREE_CHANNEL_ID

    for column in ("email", "nickname", "hashed_password", "role", "plan", "quota_left", "balance_fen"):
        check(hasattr(User, column), f"User.{column}")
    check(hasattr(SystemModelChannelRow, "api_key_ciphertext"), "SystemModelChannelRow.api_key_ciphertext")
    check(TOKENFREE_CHANNEL_ID == "tokenfree", "TokenFree channel id")
    check(verify_password("selftest-password", hash_password("selftest-password")), "password hashing")
    check(_decrypt_secret(_encrypt_secret("selftest")) == "selftest", "secret encryption")

    print("[selftest] ok", flush=True)


if __name__ == "__main__":
    main()
