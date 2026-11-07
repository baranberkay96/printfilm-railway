# PRINTFILM admin console for Railway (community template).
#
# Builds upstream's admin/ (React + Vite + Tailwind) from the v0.3.0 release exactly like upstream's
# admin/Dockerfile (the console calls same-origin /api), and serves it with Caddy instead
# of nginx: upstream's nginx.conf hard-codes the compose host `api:8000`, while this front reads
# the API's private address from PRINTFILM_API at start. Routing mirrors upstream's nginx.conf.
#
# Upgrade: change commit and sha256 below (and in services/api and services/web).

ARG NODE_IMAGE=node:22.23.4-alpine@sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202
ARG CADDY_IMAGE=caddy:2.11.9-alpine@sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee

# ── Stage 1: pinned, checksum-verified source ───────────────────────────────
FROM ${NODE_IMAGE} AS source
RUN apk add --no-cache ca-certificates curl
RUN set -eu; \
    commit="345495e050bd0a39065c49ff6b3e87cf506a2a0d"; \
    sha256="38eb5b66969a83f5e9821f6b8b0bc1ff06b335260d60f24d5c14adceaac9f568"; \
    curl --retry 5 --retry-all-errors --retry-delay 5 --connect-timeout 30 -fsSL \
      -o /tmp/printfilm.tar.gz "https://codeload.github.com/yi1108/printfilm/tar.gz/${commit}"; \
    echo "${sha256}  /tmp/printfilm.tar.gz" | sha256sum -c -; \
    mkdir /src; \
    tar -xzf /tmp/printfilm.tar.gz -C /src --strip-components=1; \
    rm -f /tmp/printfilm.tar.gz; \
    for f in admin/package.json admin/package-lock.json admin/index.html admin/src/main.tsx; do \
      [ -f "/src/$f" ] || { echo "source has no $f" >&2; exit 1; }; \
    done; \
    rm -rf /src/admin/node_modules /src/admin/dist

# ── Stage 2: build (upstream admin/Dockerfile) ──────────────────────────────
FROM ${NODE_IMAGE} AS build
WORKDIR /src
COPY --from=source /src/admin/package.json /src/admin/package-lock.json ./
RUN npm ci --no-audit --no-fund --fetch-retries=5 --fetch-retry-maxtimeout=120000
COPY --from=source /src/admin/ ./
RUN npm run build && test -f dist/index.html

# ── Stage 3: Caddy ──────────────────────────────────────────────────────────
FROM ${CADDY_IMAGE}
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv
# Fail the build on a Caddyfile error instead of at deploy time (placeholder address for the check).
RUN PRINTFILM_API=api.railway.internal:8000 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
ENV PORT=8080
EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
