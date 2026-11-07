"""Pre-deploy step of the PRINTFILM API service (community template), run by ``start.sh predeploy``.

1. Wait for Postgres (services start in parallel; a fresh database can take a minute).
2. Create and patch the tables with upstream's own startup functions (``init_db`` =
   ``create_all``, then ``_apply_schema_patches``). The app repeats both at start; running them
   here first means the admin login below can be written on the very first deploy.
3. Sync the admin login from ADMIN_EMAIL / ADMIN_PASSWORD. Upstream has no way to create an admin:
   ``ADMIN_BOOTSTRAP_EMAILS`` only promotes accounts that registered themselves, and sign-up is
   closed by this template. The account is created if missing, otherwise promoted to admin and its
   password reset to ADMIN_PASSWORD when it differs (the variable stays the source of truth).
4. Fill the TokenFree key while none is saved. Upstream imports OPENAI_API_KEY into its TokenFree
   channel only on the very first start; a key added to the service later would be ignored. A key
   saved in the admin console is never overwritten.

Exits non-zero (failing the deploy) only when Postgres stays unreachable, the schema step fails, or
ADMIN_PASSWORD is shorter than 12 characters. An invalid ADMIN_EMAIL falls back to the default.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, "/app")

DEFAULT_ADMIN_EMAIL = "admin@example.com"
ADMIN_NICKNAME = "Admin"
MIN_PASSWORD = 12
BCRYPT_MAX_BYTES = 72


def log(message: str) -> None:
    print(f"[railway] {message}", file=sys.stderr, flush=True)


def fail(message: str) -> None:
    log(f"error: {message}")
    sys.exit(1)


def admin_email() -> str:
    from email_validator import EmailNotValidError, validate_email

    raw = os.environ.get("ADMIN_EMAIL", "").strip()
    try:
        # Same check as upstream's login form (pydantic EmailStr); upstream stores e-mails lower-cased.
        return validate_email(raw or DEFAULT_ADMIN_EMAIL, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        log(f"warning: ADMIN_EMAIL {raw!r} is not a valid address ({exc}); using {DEFAULT_ADMIN_EMAIL}")
        return DEFAULT_ADMIN_EMAIL


def admin_password() -> str:
    password = os.environ.get("ADMIN_PASSWORD", "")
    if len(password) < MIN_PASSWORD:
        fail(
            f"ADMIN_PASSWORD must be at least {MIN_PASSWORD} characters "
            "(the admin console is on a public URL); the template generates one"
        )
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        log(f"warning: ADMIN_PASSWORD is longer than {BCRYPT_MAX_BYTES} bytes; bcrypt only uses the first {BCRYPT_MAX_BYTES}")
    return password


async def wait_for_database(limit: int) -> None:
    from sqlalchemy import text

    from app.database import engine

    started = time.monotonic()
    while True:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - any connect error means "not yet"
            waited = int(time.monotonic() - started)
            if waited >= limit:
                fail(f"Postgres did not accept connections within {limit}s: {exc}")
            log(f"waiting for Postgres ({waited}s): {type(exc).__name__}")
            await asyncio.sleep(5)


async def prepare_schema() -> None:
    from app.database import init_db
    from app.main import _apply_schema_patches

    await init_db()
    await _apply_schema_patches()
    log("schema ready (upstream create_all + additive patches)")


async def sync_admin(email: str, password: str) -> None:
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import AsyncSessionLocal
    from app.models import User
    from app.services.auth import hash_password, verify_password

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is None:
            db.add(
                User(
                    email=email,
                    nickname=ADMIN_NICKNAME,
                    hashed_password=hash_password(password),
                    role="admin",
                    plan="free",
                    quota_left=get_settings().new_user_quota,
                    balance_fen=0,
                )
            )
            await db.commit()
            log(f"admin login created: {email}")
            return

        changed = []
        if (user.role or "user") != "admin":
            user.role = "admin"
            changed.append("promoted to admin")
        try:
            same = verify_password(password, user.hashed_password or "")
        except (ValueError, TypeError):
            same = False
        if not same:
            user.hashed_password = hash_password(password)
            changed.append("password set from ADMIN_PASSWORD")
        if changed:
            await db.commit()
            log(f"admin login {email}: {', '.join(changed)}")
        else:
            log(f"admin login {email}: unchanged")


async def fill_tokenfree_key() -> None:
    key = (os.environ.get("TOKENFREE_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        return

    from app.database import AsyncSessionLocal
    from app.models_settings import SystemModelChannelRow
    from app.services.model_settings import _decrypt_secret, _encrypt_secret
    from app.services.tokenfree_gateway import TOKENFREE_CHANNEL_ID

    async with AsyncSessionLocal() as db:
        row = await db.get(SystemModelChannelRow, TOKENFREE_CHANNEL_ID)
        if row is None:
            log("TokenFree key: first start, the app imports TOKENFREE_API_KEY itself")
            return
        if _decrypt_secret(row.api_key_ciphertext or ""):
            log("TokenFree key: a key is already saved (change it in Admin -> System settings -> Models); TOKENFREE_API_KEY not applied")
            return
        row.api_key_ciphertext = _encrypt_secret(key)
        await db.commit()
        log("TokenFree key: no key was saved; stored TOKENFREE_API_KEY in the TokenFree channel")


async def main() -> None:
    email = admin_email()
    password = admin_password()
    try:
        limit = max(30, int(os.environ.get("TEMPLATE_DB_WAIT_SECONDS", "600")))
    except ValueError:
        limit = 600

    from app.database import dispose_engine

    try:
        await wait_for_database(limit)
        await prepare_schema()
        await sync_admin(email, password)
        try:
            await fill_tokenfree_key()
        except Exception as exc:  # noqa: BLE001 - optional convenience, never fails the deploy
            log(f"warning: could not store TOKENFREE_API_KEY ({type(exc).__name__}: {exc}); set it in the admin console")
    finally:
        await dispose_engine()


if __name__ == "__main__":
    os.chdir("/app")
    asyncio.run(main())
