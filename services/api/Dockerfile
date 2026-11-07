# PRINTFILM API for Railway (community template).
#
# Upstream publishes images only as `latest`/`v0.3.0` tags on an Aliyun registry, so this builds
# upstream's own backend/Dockerfile steps from the v0.3.0 release instead: the source is the
# codeload tarball of the tag's commit, checked against a SHA-256 before anything runs.
#
# Runtime differences from upstream's image (see TEMPLATE.md): it runs as an unprivileged user
# after preparing the media volume, serves on a dual-stack socket from $PORT, wraps the app with
# two template switches (railway/railway_app.py), caps FFmpeg threads to the service's CPU quota,
# and has a pre-deploy step (schema + admin login). Upstream's Python code is not modified.
#
# Upgrade: change version, commit and sha256 below (and in services/web and services/admin).

ARG PYTHON_IMAGE=python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

# ── Stage 1: pinned, checksum-verified source ───────────────────────────────
FROM ${PYTHON_IMAGE} AS source
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
RUN set -eu; \
    version="v0.3.0"; \
    commit="345495e050bd0a39065c49ff6b3e87cf506a2a0d"; \
    sha256="38eb5b66969a83f5e9821f6b8b0bc1ff06b335260d60f24d5c14adceaac9f568"; \
    curl --retry 5 --retry-all-errors --retry-delay 5 --connect-timeout 30 -fsSL \
      -o /tmp/printfilm.tar.gz "https://codeload.github.com/yi1108/printfilm/tar.gz/${commit}"; \
    echo "${sha256}  /tmp/printfilm.tar.gz" | sha256sum -c -; \
    mkdir /src; \
    tar -xzf /tmp/printfilm.tar.gz -C /src --strip-components=1; \
    rm -f /tmp/printfilm.tar.gz; \
    for f in backend/requirements.txt backend/app/main.py backend/app/config.py backend/app/services/storage.py backend/static/templates; do \
      [ -e "/src/$f" ] || { echo "source has no $f" >&2; exit 1; }; \
    done; \
    printf 'PRINTFILM %s (%.12s)\n' "$version" "$commit" > /src/backend/.printfilm-release

# ── Stage 2: runtime (upstream backend/Dockerfile) ──────────────────────────
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    MALLOC_ARENA_MAX=2

WORKDIR /app

# FFmpeg composes the final cuts; the WenQuanYi font renders Chinese burned-in captions (upstream's
# choice). Debian packages follow Debian security updates; setpriv/mountpoint/timeout come from the
# base system and are used by railway/start.sh and the checks below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-wqy-zenhei \
 && rm -rf /var/lib/apt/lists/* \
 && ffmpeg -hide_banner -version | head -n 1 \
 && test -f /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc \
 && command -v setpriv \
 && command -v mountpoint \
 && command -v timeout

COPY --from=source /src/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --retries 5 --timeout 60 -r /app/requirements.txt

COPY --from=source /src/backend/app /app/app
COPY --from=source /src/backend/static /app/static
COPY --from=source /src/backend/.printfilm-release /app/.printfilm-release
COPY --chmod=0755 railway/ /app/railway/

# Unprivileged runtime user; /app/static is the only tree the app writes to (generated media is the
# volume at /app/static/generated, mock/voice-preview caches stay in the image layer).
# The ffmpeg wrapper goes ahead of /usr/bin on PATH (railway/ffmpeg explains why).
RUN groupadd --system --gid 1000 printfilm \
 && useradd --system --uid 1000 --gid 1000 --create-home --home-dir /home/printfilm --shell /usr/sbin/nologin printfilm \
 && mkdir -p /app/static/generated /app/static/voice_previews /app/static/mock /app/static/site \
 && chown -R printfilm:printfilm /app/static \
 && ln -s /app/railway/ffmpeg /usr/local/bin/ffmpeg \
 && sh -n /app/railway/start.sh \
 && sh -n /app/railway/ffmpeg \
 && python -m py_compile /app/railway/railway_app.py /app/railway/serve.py /app/railway/bootstrap.py /app/railway/selftest.py \
 && rm -rf /app/railway/__pycache__

# Build-time checks: the FFmpeg wrapper with libx264 and the caption font, then the upstream names the
# template's Python files rely on (no database or network needed).
RUN set -eu; \
    test "$(command -v ffmpeg)" = /usr/local/bin/ffmpeg; \
    PRINTFILM_FFMPEG_THREADS=2 ffmpeg -hide_banner -loglevel error -y \
      -f lavfi -i testsrc2=duration=1:size=320x240:rate=10 \
      -f lavfi -i anullsrc=r=44100:cl=mono -t 1 \
      -vf "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text=ok:fontsize=24:x=10:y=10" \
      -c:v libx264 -pix_fmt yuv420p -c:a aac /tmp/railway-selftest.mp4; \
    test -s /tmp/railway-selftest.mp4; \
    PRINTFILM_FFMPEG_THREADS=0 ffmpeg -hide_banner -loglevel error -i /tmp/railway-selftest.mp4 -f null -; \
    rm -f /tmp/railway-selftest.mp4; \
    cd /app; \
    timeout 300 python /app/railway/selftest.py; \
    rm -rf /app/railway/__pycache__; \
    cat /app/.printfilm-release

EXPOSE 8000
# Starts as root only to hand the media volume (mounted root-owned) to the printfilm user;
# start.sh drops privileges before any app code runs.
CMD ["/app/railway/start.sh", "api"]
