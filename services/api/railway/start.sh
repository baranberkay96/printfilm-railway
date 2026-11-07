#!/bin/sh
# PRINTFILM API on Railway (community template): one script for both roles of this image.
#
#   start.sh api        FastAPI + upstream's in-process task runtime (scheduler, executor, poller)
#                       on $PORT, media on the volume at /app/static/generated
#   start.sh predeploy  the API service's pre-deploy command: wait for Postgres, create/patch the
#                       tables exactly as the app does at start, sync the admin login, fill the
#                       TokenFree key while none is saved (railway/bootstrap.py)
#
# Railway runs pre-deploy commands without the image's entrypoint and without the volume, so this
# script repeats everything the app needs in both roles. It starts as root only to hand the volume
# (mounted root-owned) to the printfilm user, then re-executes itself unprivileged.
set -eu

ROLE="${1:-api}"
SELF="$(readlink -f "$0")"
APP_DIR=/app
MEDIA_DIR=/app/static/generated
RUN_USER=printfilm

log() { printf '[railway] %s\n' "$*"; }
warn() { printf '[railway] warning: %s\n' "$*" >&2; }
fail() { printf '[railway] error: %s\n' "$*" >&2; exit 1; }

case "$ROLE" in
  api | predeploy) ;;
  *) fail "usage: start.sh api|predeploy (got '${ROLE}')" ;;
esac

# ── root: prepare the volume, then drop privileges ──────────────────────────
if [ "$(id -u)" = 0 ]; then
  if [ "$ROLE" = api ]; then
    mkdir -p "$MEDIA_DIR"
    if ! mountpoint -q "$MEDIA_DIR"; then
      warn "${MEDIA_DIR} is not a mounted volume: generated images, videos and uploads are lost on every redeploy"
    fi
    # Only entries that are not printfilm's yet (a fresh volume, files restored as root); lost+found stays root's.
    if [ -n "$(find "$MEDIA_DIR" -xdev -path "$MEDIA_DIR/lost+found" -prune -o ! -user "$RUN_USER" -print -quit)" ]; then
      log "giving ${MEDIA_DIR} to ${RUN_USER}"
      find "$MEDIA_DIR" -xdev -path "$MEDIA_DIR/lost+found" -prune -o ! -user "$RUN_USER" -exec chown "$RUN_USER:$RUN_USER" {} +
    fi
  fi
  exec setpriv --reuid="$RUN_USER" --regid="$RUN_USER" --init-groups --no-new-privs -- \
    env HOME=/home/printfilm USER="$RUN_USER" "$SELF" "$@"
fi

cd "$APP_DIR"
export PYTHONPATH="${APP_DIR}${PYTHONPATH:+:$PYTHONPATH}"
RELEASE="$(cat "$APP_DIR/.printfilm-release" 2>/dev/null || echo 'PRINTFILM')"

# ── database URLs ───────────────────────────────────────────────────────────
# Upstream needs postgresql+asyncpg:// (API, task runtime) and postgresql+psycopg2:// (sync helpers).
# The template passes Railway's plain postgresql:// URL; any PostgreSQL URL typed in is converted too.
normalize_database_urls() {
  url="${DATABASE_URL:-}"
  [ -n "$url" ] || fail "DATABASE_URL is empty (reference the Postgres service: \${{Postgres.DATABASE_URL}})"
  case "$url" in
    postgresql+asyncpg://*) rest="${url#postgresql+asyncpg://}" ;;
    postgresql+*://*) rest="${url#postgresql+*://}" ;;
    postgresql://*) rest="${url#postgresql://}" ;;
    postgres://*) rest="${url#postgres://}" ;;
    *) fail "DATABASE_URL is not a PostgreSQL URL (PRINTFILM supports PostgreSQL only)" ;;
  esac
  # asyncpg spells libpq's sslmode as ssl
  DATABASE_URL="postgresql+asyncpg://$(printf '%s' "$rest" | sed 's/\([?&]\)sslmode=/\1ssl=/')"
  if [ -z "${DATABASE_URL_SYNC:-}" ]; then
    DATABASE_URL_SYNC="postgresql+psycopg2://${rest}"
  fi
  export DATABASE_URL DATABASE_URL_SYNC
}

# Upstream falls back to a well-known JWT/encryption key when SECRET_KEY is missing: refuse that.
check_secret_key() {
  key="${SECRET_KEY:-}"
  case "$key" in
    '' | dev-secret-change-me | change-me-to-a-long-random-string)
      fail "SECRET_KEY is empty or an upstream example value; set a long random value (the template generates one)" ;;
  esac
  if [ "${#key}" -lt 32 ]; then
    warn "SECRET_KEY is shorter than 32 characters; it signs logins and encrypts the saved TokenFree key"
  fi
}

normalize_database_urls
check_secret_key

# One input for upstream's two key variables (text and media share the TokenFree key).
if [ -n "${TOKENFREE_API_KEY:-}" ]; then
  : "${OPENAI_API_KEY:=$TOKENFREE_API_KEY}"
  : "${ARK_API_KEY:=$TOKENFREE_API_KEY}"
  export OPENAI_API_KEY ARK_API_KEY
fi

# FFmpeg/x264 size thread pools from the host's CPUs, not the service's quota (railway/ffmpeg).
ffmpeg_threads() {
  want="${PRINTFILM_FFMPEG_THREADS:-}"
  case "$want" in
    '' | auto) ;;
    *[!0-9]*)
      warn "PRINTFILM_FFMPEG_THREADS='${want}' is not a number; using the automatic value"
      ;;
    *) echo "$want"; return ;;
  esac
  n="$(nproc 2>/dev/null || echo 1)"
  if [ -r /sys/fs/cgroup/cpu.max ]; then
    read -r quota period < /sys/fs/cgroup/cpu.max || true
    case "${quota:-max}:${period:-0}" in
      max:* | *:0) ;;
      *[!0-9:]*) ;;
      *)
        q=$(( (quota + period - 1) / period ))
        [ "$q" -lt "$n" ] && n="$q"
        ;;
    esac
  fi
  [ "$n" -gt 8 ] && n=8
  [ "$n" -lt 1 ] && n=1
  echo "$n"
}

memory_limit_mib() {
  if [ -r /sys/fs/cgroup/memory.max ]; then
    v="$(cat /sys/fs/cgroup/memory.max)"
    case "$v" in
      '' | max | *[!0-9]*) ;;
      *) echo $((v / 1048576)) ;;
    esac
  fi
}

case "$ROLE" in
  predeploy)
    log "pre-deploy for ${RELEASE}: schema and admin login"
    exec python "$APP_DIR/railway/bootstrap.py"
    ;;

  api)
    [ -w "$MEDIA_DIR" ] || fail "${MEDIA_DIR} is not writable by $(id -un); attach the volume at ${MEDIA_DIR}"
    # The admin password is only needed by the pre-deploy step.
    unset ADMIN_PASSWORD

    PRINTFILM_FFMPEG_THREADS="$(ffmpeg_threads)"
    export PRINTFILM_FFMPEG_THREADS

    mem="$(memory_limit_mib)"
    if [ -n "$mem" ] && [ "$mem" -lt 1536 ]; then
      warn "memory limit is ${mem} MiB: browsing and single generations fit, but composing long videos with FFmpeg can exceed it and restart the API (Hobby plan or more recommended)"
    fi
    [ -n "${REDIS_URL:-}" ] || warn "REDIS_URL is empty: live progress and password-reset links need Redis"
    case "${PUBLIC_BASE_URL:-}" in
      https://*) ;;
      *) warn "PUBLIC_BASE_URL '${PUBLIC_BASE_URL:-}' is not https://...: links in e-mails and public media URLs for video generation need the Web service's https address" ;;
    esac
    if [ -z "${OPENAI_API_KEY:-}" ]; then
      log "no TokenFree key in the environment: add it in Admin -> System settings -> Models (or set TOKENFREE_API_KEY and redeploy)"
    fi

    if [ "$PRINTFILM_FFMPEG_THREADS" = 0 ]; then threads_label="FFmpeg default"; else threads_label="$PRINTFILM_FFMPEG_THREADS"; fi
    log "${RELEASE} API on [::]:${PORT:-8000}; media ${MEDIA_DIR}; ffmpeg threads ${threads_label}; memory limit ${mem:-none}${mem:+ MiB}; sign-up ${PRINTFILM_SIGNUP_ENABLED:-false}"
    exec python "$APP_DIR/railway/serve.py"
    ;;
esac
