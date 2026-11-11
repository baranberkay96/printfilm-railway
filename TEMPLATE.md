# PRINTFILM AI Short Video and Drama Studio — Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **PRINTFILM AI Short Video and Drama Studio** (46 chars; `v0.3` = pinned release v0.3.0; upstream's own spelling is all caps) |
| Description | AI short video and short drama studio: script to storyboard to final cut. (73 chars) |
| Category | AI/ML |
| Tags | printfilm, ai-video, short-video, short-drama, storyboard, seedance, seedream, ffmpeg, fastapi |
| Icon | `https://cdn.jsdelivr.net/gh/yi1108/printfilm@345495e050bd0a39065c49ff6b3e87cf506a2a0d/frontend/public/favicon.svg` (upstream's app favicon at the release commit; HTTP 200 `image/svg+xml`, checked 2026-11-07). The admin favicon is Vite's default logo, not used. |
| Repo | `baranberkay96/printfilm-railway`, root directories `/services/web`, `/services/admin`, `/services/api` |
| User input at deploy | **None required.** Optional `TOKENFREE_API_KEY` (API). Admin password and all secrets are generated. |

**Listing wording, checked against the code:** the user app's two product lines ("AI short video", `kepu`, and "drama") both run LLM script → storyboard → Seedream images → Seedance video → FFmpeg final cut (`services/pipeline.py`, `services/drama/*`, `ffmpeg_compose.py`, `drama/episode_compose.py`). The description holds once a TokenFree key is set. Without a key the app boots, and sign-in, browsing templates and the admin console work, but nothing generates. The README says so.

## Base market template

None. `_market/` is empty, and the task brief says no Railway template exists for PRINTFILM. The base is upstream's own `docker-compose.full.yml` (build from source) and `deploy/.env.docker.example` at v0.3.0.

## Pinned versions

| Component | Source | Version / digest | Date | Checked |
|---|---|---|---|---|
| PRINTFILM (API, web, admin) | `github.com/yi1108/printfilm` codeload tarball of tag `v0.3.0` = commit `345495e050bd0a39065c49ff6b3e87cf506a2a0d` | SHA-256 `38eb5b66969a83f5e9821f6b8b0bc1ff06b335260d60f24d5c14adceaac9f568` (47.2 MB; downloaded twice, same hash) | released 2026-10-15 | 2026-11-07 |
| API base | `python:3.12.16-slim-bookworm` | index `sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df` (amd64 present) | pushed 2026-11-05 | 2026-11-07 |
| FFmpeg, caption font | Debian 12 `ffmpeg` (5.1.x), `fonts-wqy-zenhei` | unpinned Debian packages (follow security updates; Rule 8.27) | — | — |
| Web/Admin build | `node:22.23.4-alpine` | index `sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202` | pushed 2026-11-05 | 2026-11-07 |
| Web/Admin runtime | `caddy:2.11.9-alpine` | index `sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee` | 2026-11-06 | 2026-11-07 |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl:18` | tag (from `_railway-base`; index `sha256:4fc833b4…` today) | — | 2026-11-07 |
| Redis | `redis:8.2` | tag (from `_railway-base`; index `sha256:b0b01167…` today) | — | 2026-11-07 |

Upstream pins Python 3.12 slim bookworm, node 22 alpine, nginx 1.27, postgres 16 and redis 7. Postgres 18 and Redis 8.2 follow the collection's base services. PRINTFILM uses only `create_all` plus additive `ALTER TABLE` and plain Redis commands.

**Upstream images not used.** Aliyun ACR `gcc-registry.cn-hangzhou.cr.aliyuncs.com/gcc/printfilm-{api,web,admin-web}` have anonymous `v0.3.0` tags. Each equals `latest` (index digests `a68e123b…`, `363899fa…`, `944a2c7f…`, checked 2026-11-07). They were not used for three reasons. Their correspondence to the v0.3.0 source can't be proven without layer forensics. The web/admin nginx configs hard-code `proxy_pass http://api:8000` (a compose host name that doesn't exist on Railway). Pulls from cn-hangzhou to Railway's regions are an extra reliability risk. The template builds the same three Dockerfiles from the verified tarball instead.

**Upgrade path:** set the commit and SHA-256 in `services/api/Dockerfile`, `services/web/Dockerfile` and `services/admin/Dockerfile` (and the version label in the API one). Diff upstream's three Dockerfiles, nginx confs, `deploy/.env.docker.example` and `backend/app/main.py` (startup, schema patches). Then rebuild all three; the API build's self-test fails if a name the template uses has moved. Rename the listing when the minor version changes (v0.4). Note: v0.3.0's FastAPI app and README still say `0.2.0`; upstream did not bump them.

## Architecture

```
Internet --HTTPS--> Web (Caddy :8080, public)                     Admin (Caddy :8080, public)
                     |- /healthz -> ok                              |- /healthz -> ok
                     |- /epay/notify -> API /api/billing/epay/notify |- /api/*, /static/* -> API
                     |- /api/*, /static/* -> API (64 MB body cap,    '- admin SPA (Chinese only)
                     |     streaming, 30 s retry during redeploys)
                     '- user SPA (zh/en)
API (private, [::]:8000 dual-stack, 1 replica, volume /app/static/generated, runs as uid 1000)
   |- pre-deploy: wait for Postgres -> create_all + schema patches -> admin login sync -> TokenFree key fill
   |- FastAPI + in-process task runtime (scheduler / executor / poller / watchdog; no Celery worker)
   |- FFmpeg (thread-capped wrapper) for final cuts, captions (WenQuanYi), frames, audio
   |- railway_app.py: sign-up switch, public media URLs while OSS is off
   |- Postgres (asyncpg + psycopg2), Redis (progress pub/sub, reset tokens)
   '- outbound: www.tokenfree.com (text, image, video, voice, price list); edge-tts fallback (Microsoft)
```

### Deviations from upstream's Docker setup (v0.3.0) and why

- **Built from the release tarball** with a SHA-256 check, not from a checkout or the ACR `latest` images.
- **Caddy instead of nginx** for Web and Admin. Upstream's `nginx.conf` hard-codes `api:8000`, so Caddy reads `PRINTFILM_API` (`${{API.RAILWAY_PRIVATE_DOMAIN}}:${{API.PORT}}`) and resolves it per request. Caddy starts before the API exists, and nginx would fail on an unresolvable upstream at start. Routes are identical (`/epay/notify` rewrite, `/api/`, `/static/`, SPA fallback). Additions: `/healthz`, unbuffered streaming (as `proxy_buffering off`), a 30 s retry window while the API restarts, a body cap of 64 MB instead of 512 MB, cache headers for hashed assets, and basic security headers (Admin: `noindex`, `DENY` framing).
- **Admin login created.** Upstream has no seed account; `ADMIN_BOOTSTRAP_EMAILS` only promotes users who registered themselves. The API's pre-deploy step creates or updates the admin account from `ADMIN_EMAIL`/`ADMIN_PASSWORD` (generated, 32 characters), using upstream's own `hash_password`. It promotes the account and resets its password when it differs, on every deploy.
- **Sign-up closed by default.** Upstream registration is open to anyone who reaches the site, and with billing off (upstream default) every account generates on the operator's TokenFree key. `POST /api/auth/register` answers 403 with a bilingual message unless `PRINTFILM_SIGNUP_ENABLED=true`. This is done in an ASGI wrapper (`railway_app.py`), so the rule holds whichever front the request comes through. Admin access remains upstream's role check on every `/api/admin` route.
- **Public media URLs while OSS is off.** Seedance needs public HTTPS reference images/audio. Upstream's only source is Aliyun OSS (`oss2`, not S3-compatible); with OSS off, `republish_url` returns `/static/...`. `_resolve_image_ref(prefer_https=True)` then raises "Seedance 需要公网可访问的图片 URL" for uploaded images, asset-library pictures and generated images whose provider link has expired. The wrapper makes `republish_url` return `PUBLIC_BASE_URL/static/...` (the Web domain serves `/static/`) when the file exists locally, OSS is off and the base URL is https. Upstream already maps such URLs back to local files (`local_path_from_url`, `is_local_static_url`). Switch: `PRINTFILM_PUBLIC_MEDIA_URLS=false`.
- **TokenFree key fill.** Upstream imports `OPENAI_API_KEY` into its TokenFree channel only on the very first start; later env changes are ignored, because the DB overlay wins. The pre-deploy step stores `TOKENFREE_API_KEY` into the channel only while no key is saved (encrypted with upstream's `_encrypt_secret`). `TOKENFREE_API_KEY` also feeds `OPENAI_API_KEY`/`ARK_API_KEY` for upstream's first-start import.
- **Unprivileged runtime.** Upstream runs as root. Here `start.sh` gives the root-owned Railway volume to uid 1000 (only entries not yet owned), then `setpriv --no-new-privs`. The pre-deploy step runs unprivileged too.
- **Dual-stack listener from `PORT`.** `serve.py` binds one `::` socket with `IPV6_V6ONLY=0` and passes it to uvicorn (`Server.run(sockets=…)`), still one worker. Upstream's `--host 0.0.0.0` would miss IPv6-only private networks; `--host ::` would be IPv6-only (Rules 8.1, 8.2, 8.14). It also trusts proxy headers (only Caddy reaches it) and waits ≤ 180 s for Postgres/Redis. Upstream disables Redis for the life of the process after one failed connection.
- **FFmpeg thread cap (Rule 8.15).** `/usr/local/bin/ffmpeg` wraps Debian's binary. It adds `-filter_threads N -filter_complex_threads N`, `-threads N` before each `-i`, and before the output. N = the cgroup CPU quota (max 8); override with `PRINTFILM_FFMPEG_THREADS` (`0` = unchanged). All 29 FFmpeg argument lists in v0.3.0 end with the output path (AST scan). The wrapper is exercised with libx264 + drawtext at build.
- **Database URLs derived** from Railway's plain `postgresql://` URL (`+asyncpg`, `+psycopg2`; `sslmode`→`ssl` for asyncpg). Upstream's insecure `SECRET_KEY` defaults are refused.
- **Schema and admin in pre-deploy (Rule 8.6),** with a 600 s Postgres wait; the app repeats `create_all` + patches at start, as upstream does.
- **Redis** gets upstream's `--maxmemory 512mb --maxmemory-policy allkeys-lru` on top of the base service (append-only file not kept: all keys are short-lived).
- **Not used:** upstream's Celery leftovers (`USE_CELERY` is not read in v0.3.0), `deploy/docker-compose.yml` (infra-only), OSS/Epay deployment scripts.

### What could not be bundled

- **Model inference.** The open-source build only talks to TokenFree (`tokenfree_gateway.py` locks the base URL). No other provider, and no self-hosted model, can be plugged in without code changes.
- **Railway Bucket.** Upstream's object storage is Aliyun OSS via `oss2` (OSS signatures, not S3), so a Bucket would have no function. Media lives on the API volume, as in upstream's compose (`printfilm_media:/app/static/generated`). Users with Aliyun OSS can still enable it in the admin console.
- **Payments.** Epay (`pay.gitcc.com`, China) is supported upstream and reachable via `/epay/notify`, but not configured.

## Services

Service names matter: Web and Admin reference `API`, and API references `Postgres`, `Redis`, `Web`, `Admin`. Creation order does not matter.

### Web
- **Source:** repo `baranberkay96/printfilm-railway`, root `/services/web` (tarball → `npm ci` → `vite build` with `VITE_API_BASE=` → Caddy; `caddy validate` at build)
- **Start:** image default · **Healthcheck:** `/healthz` (120 s) · **Public domain:** yes → 8080 · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8080` | Caddy port; public domain and healthcheck use it. |
| `PRINTFILM_API` | `${{API.RAILWAY_PRIVATE_DOMAIN}}:${{API.PORT}}` | Where `/api/*`, `/static/*`, `/epay/notify` go. |

### Admin
- Same as Web, root `/services/admin` (upstream `admin/`), no `/epay/notify`.

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8080` | Caddy port. |
| `PRINTFILM_API` | `${{API.RAILWAY_PRIVATE_DOMAIN}}:${{API.PORT}}` | Where `/api/*`, `/static/*` go. |

### API
- **Source:** repo, root `/services/api` (tarball → Python 3.12 + FFmpeg + upstream requirements → build-time FFmpeg and self-tests)
- **Start:** image default (`start.sh api`) · **Pre-deploy:** `/app/railway/start.sh predeploy` (timeout 900 s) · **Healthcheck:** `/api/health` (600 s) · **Public domain:** no · **Volume:** `/app/static/generated` · **Restart:** ALWAYS · **Replicas:** 1

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Dual-stack listen port; healthcheck. |
| `TOKENFREE_API_KEY` | empty (optional input) | TokenFree key for all generation; can be added later in the admin console. |
| `ADMIN_EMAIL` | `admin@example.com` | Admin login; invalid → default with a warning (Rule 8.29). |
| `ADMIN_PASSWORD` | `${{secret(32, …)}}` | Applied every deploy; < 12 characters fails the pre-deploy (fail closed: public admin URL). |
| `SECRET_KEY` | `${{secret(64, hex)}}` | JWT signing + Fernet key for saved secrets; must never change. |
| `PRINTFILM_SIGNUP_ENABLED` | `false` | Open registration. |
| `PRINTFILM_PUBLIC_MEDIA_URLS` | `true` | Public https media URLs for Seedance while OSS is off. |
| `PRINTFILM_FFMPEG_THREADS` | `auto` | FFmpeg thread cap. |
| `PUBLIC_BASE_URL` | `https://${{Web.RAILWAY_PUBLIC_DOMAIN}}` | First start only; then admin → Site. |
| `CORS_ORIGINS` | Web + Admin https origins | Avoids upstream's `*` fallback. |
| `MODEL_LLM` / `MODEL_IMAGE` / `MODEL_VIDEO` | `kimi-k2.6` / `seedream-5-0-pro` / `seedance-2-5` | Upstream's Docker defaults; first start only. |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Converted by `start.sh`. |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Progress events, reset tokens. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `30` | Clean task-runtime stop; unfinished tasks are recovered as orphans. |

Optional upstream knobs, not pre-created (all also editable in the admin console, which wins after the first start): `ARK_MOCK`, `BILLING_ENABLED`, `ARK_VIDEO_RESOLUTION` (480p), `TASK_RUNTIME_MAX_CONCURRENCY` (4), `TASK_USER_MAX_CONCURRENCY` (4), `SMTP_*`, `OSS_*`, `VOLC_TTS_*`, `EPAY_*`.

### Postgres / Redis
- From `_railway-base` (`postgres-ssl:18`, volume `/var/lib/postgresql/data`; `redis:8.2`, volume `/data`, plus maxmemory flags). Private only, restart ON_FAILURE (10).

## Improvements over market templates

No market template exists, so this compares with running upstream's Docker setup unchanged.

| # | Upstream `docker-compose(.full).yml` as is | This template |
|---|---|---|
| 1 | `latest` images from an Aliyun registry, or build from a local checkout | v0.3.0 built from a SHA-256-verified tarball; base images pinned by digest |
| 2 | nginx fronts hard-code `api:8000` | Caddy fronts read the API address; start without the API; retry during redeploys |
| 3 | No admin account; promote-after-register only | Admin login generated and synced by pre-deploy |
| 4 | Open registration spends the operator's key | Sign-up closed unless enabled |
| 5 | Video from uploaded or old images fails without Aliyun OSS | Local media handed to Seedance via the public Web domain |
| 6 | API runs as root | Volume ownership fixed, then unprivileged with no-new-privs |
| 7 | Port 8000 fixed, `0.0.0.0` | `PORT`, dual-stack socket, proxy headers |
| 8 | FFmpeg/x264 threads from host CPUs | Capped to the CPU quota |
| 9 | Key in env only read on first start | Key filled later while none is saved |
| 10 | 512 MB request bodies into a process that reads uploads in memory | 64 MB cap (upstream's largest limit is 40 MB) |
| 11 | Weak example `SECRET_KEY`/passwords in example env | Generated secrets; upstream defaults refused |
| 12 | Runtime surprises only at deploy | Build-time FFmpeg + self-test of every upstream name used |

## Scaling

- **API: 1 replica.** The task runtime (scheduler, poller, leases) lives in the process, and the volume belongs to one service. Scale vertically; raise `TASK_RUNTIME_MAX_CONCURRENCY` in the admin console with more CPU/RAM.
- **Web/Admin:** stateless Caddy; 1 replica is plenty.
- **Throughput** is bounded by TokenFree queues and rate limits (Seedance clips take minutes each), not by Railway.
- **Volume:** generated images, clips and final cuts accumulate under `p{id}/`. Hobby's 5 GB holds a few dozen shorts; heavier use needs Pro or clean-ups.

## Resource estimate

Prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month. **Estimates from the code paths, not measurements** (nothing was run).

| Service | Idle RAM | Typical RAM | vCPU idle / busy | Volume |
|---|---|---|---|---|
| API (FastAPI, SQLAlchemy, task runtime) | 250–350 MB | 400–700 MB | 0.02 / 0.1 | media: 0.1 GB at start, ~20–100 MB per short |
| API FFmpeg composing (while running) | 0 | +200–600 MB (720p x264, capped threads) | — / 1–2 | — |
| Postgres | 60–100 MB | 100–200 MB | 0.01 / 0.05 | 0.2–1 GB |
| Redis | 10 MB | 20–40 MB | 0 / 0.01 | < 0.1 GB |
| Web, Admin (Caddy) | 2 × 15 MB | 2 × 30 MB | 0 / 0.02 | — |
| **Total** | **≈ 0.4 GB** | **≈ 0.8–1.2 GB** (peaks 1.5–2 GB) | **≈ 0.03 / up to 2** | **1–10 GB** |

- **Idle:** 0.4 GB × $10 + 0.03 vCPU × $20 + 1.5 GB × $0.15 ≈ **$5–6/month**.
- **Typical (small team, a few videos a week):** ≈ 0.9 GB avg, 0.15 vCPU, 10 GB volumes ≈ **$12–20/month**.
- **Heavy (daily episodes):** ≈ 1.8 GB avg, 0.5 vCPU, 50 GB ≈ **$35–40/month** (Pro for volumes > 5 GB).
- **Minimum plan: Hobby.** Trial's 1 GB per service (953 MiB in the cgroup) fits the API idle and single generations, but long compositions can exceed it. `start.sh` warns below 1.5 GiB (Rule 8.31). Trial's small volume fills fast.
- **Provider cost (TokenFree public price list, 2026-11-07, USD):** Seedream 5.0 Pro $0.062 (≤1.5K) / $0.123 (2K) per image. Seedance 2.5 base tier $14.4 per M tokens; upstream estimates 10k tokens/s at 480p and 22k at 720p, so ≈ $0.14/s and ≈ $0.32/s. A 30 s 480p short with 6 shots ≈ $4–5.
- **Build:** API image ≈ 0.7–0.9 GB (FFmpeg + Python deps + 24 MB static assets), Web/Admin ≈ 60–80 MB; not measured.

## Verification checklist

Nothing below ran yet (no Docker this round). On the first Railway deploy:

1. **Builds:** API log shows `sha256sum: OK`, the FFmpeg version line, the FFmpeg self-test, `[selftest] ok`, `PRINTFILM v0.3.0 (345495e050bd)`. Web and Admin show `Valid configuration` and finish `vite build`.
2. **Pre-deploy:** API pre-deploy logs `schema ready`, `admin login created: admin@example.com`, then (with a key) `TokenFree key: first start…`.
3. **Health:** all five services Active. `curl https://{web}/healthz` and `https://{admin}/healthz` → `ok`. The API log shows `API on [::]:8000; … ffmpeg threads N` and uvicorn `Application startup complete`. `curl https://{web}/api/health` → JSON with `"ok": true`, `"ark_mock": false`.
4. **Sign-up closed:** `curl -i -X POST https://{web}/api/auth/register -H 'content-type: application/json' -d '{"email":"a@b.co","password":"123456"}'` → 403 bilingual message. Same through `https://{admin}`.
5. **Admin:** sign in at the Admin URL with `ADMIN_EMAIL`/`ADMIN_PASSWORD` → dashboard. A non-admin token gets 403 on `/api/admin/*`.
6. **Key:** System settings → Models shows the TokenFree channel with a key (if given at deploy) and readiness for text/image/video/audio.
7. **First video (needs a funded key):** in the Web app, AI Short Video → new project → template + topic → storyboard → images → clips → final cut. `https://{web}/static/generated/p{id}/…` files load. The API log shows no "Seedance 需要公网…" error, and the final MP4 plays with captions.
8. **Image-to-video from an upload:** upload a reference image in the drama asset library and generate a clip from it. This needs `PRINTFILM_PUBLIC_MEDIA_URLS` and TokenFree/Ark being able to fetch `*.up.railway.app`.
9. **Persistence:** redeploy the API → projects, media and the admin login survive; `ls -ln /app/static/generated` shows uid 1000.
10. **Privilege drop / threads:** in the API shell, `ps -o user,args` shows `python …serve.py` as `printfilm`. During a compose, `ps` shows `ffmpeg -filter_threads N …`.
11. **Memory:** watch API memory while composing a multi-shot episode; compare with Trial's 953 MiB.
12. **Late key:** deploy without a key, then set `TOKENFREE_API_KEY` and redeploy → pre-deploy logs `stored TOKENFREE_API_KEY`.

## Open questions

- **Nothing was built or run.** The three Dockerfiles, the self-test against real upstream modules and the Caddyfiles (`caddy validate` runs in the build) are unverified until Railway builds them.
- **Seedance fetching from Railway domains:** public media URLs assume TokenFree/Volcengine Ark can download from `*.up.railway.app` (or a custom domain) quickly. If they can't, image-to-video from uploads still fails; the alternative is Aliyun OSS in the admin console.
- **Real memory use** of the API and FFmpeg is estimated, not measured (Rule 8.31).
- **TokenFree account access** for users outside China (sign-up, payment methods, model availability) was not checked. Prices are from the public JSON and are assumed to be USD (the expressions divide CNY list prices by 7.3).
- **Admin password sync** resets a password changed in the app on the next deploy (documented). A changed `ADMIN_EMAIL` creates a second admin; the first stays admin until demoted in the console.
- **Media privacy:** upstream serves `/static/` without auth at partly predictable paths (`p{id}/…`); unchanged and documented.
- **Upstream settings live in the DB after the first start** (`PUBLIC_BASE_URL`, models, billing, mock). After a custom domain, the site address must be changed in the admin console; stored absolute media URLs keep the old Railway domain, which keeps working while that domain exists.
- **Upstream pace:** `main` has moved since v0.3.0 (last push 2026-11-06), with no newer release yet.
- **edge-tts fallback** contacts Microsoft's online TTS when no Volcengine TTS is configured (upstream behaviour).
- **Upstream's Help/Contact/legal pages** describe printfilm.com's hosted service; operators should review them.

## Local verification (2026-11-07)

| Check | Result |
|---|---|
| Release tag/commit/date via GitHub API; tarball SHA-256 (downloaded twice); `diff -r` tarball vs `_upstream` | **Pass** (identical) |
| Registry digests (Docker Hub, GHCR, Aliyun ACR) and amd64 manifests | **Pass** |
| `sh -n`, `bash -n`, `dash -n` on `start.sh` and `ffmpeg` | **Pass** |
| `start.sh` under dash with stubs (`id`, `setpriv`, `mountpoint`, `find`, `nproc`, `python`, fake cgroup files): root path (chown only unowned, setpriv no-new-privs), URL conversions incl. `sslmode`, missing/non-PG DB URL, empty/default/short `SECRET_KEY`, thread cap from quota / max / nproc / explicit / invalid / 0, memory warning, http `PUBLIC_BASE_URL`, unwritable media, predeploy, bad role, `ADMIN_PASSWORD` unset for the API | **Pass** (18 cases) |
| FFmpeg wrapper with a stub binary: spaces/quotes/globs preserved, per-input and output caps, `-f null -`, option-only calls, `-version`, input-only call, 0/empty/invalid passthrough | **Pass** (11 cases) |
| `railway_app.py` against fake `app.*` modules: register 403 (trailing/double slashes), other methods/paths pass, lifespan passes, enabled/invalid flag, media URL hook (exists/missing/traversal/remote/None/OSS on/http base/switch off) | **Pass** (21 cases) |
| `bootstrap.py` against fakes: create, normalise e-mail, invalid e-mail fallback, promote + reset, unchanged (no commit), unparseable hash, short/missing password fails before DB, DB wait and give-up (fake clock), key fill / keep saved / first start / `OPENAI_API_KEY` | **Pass** (15 cases) |
| `serve.py`: URL parsing, PORT validation, dual-stack socket accepts IPv4 and IPv6, bounded wait | **Pass** |
| `template.json`: parses, every variable described, all `${{Svc.VAR}}` references resolve, `PORT` = `targetPort`, no TCP proxy, no required input; `_tools/to_serialized.py` converts it (5 services, 3 Dockerfile builds, domains on Web/Admin 8080, volumes API/Postgres/Redis) | **Pass** |
| README 7.3k chars, Rule 5 headings, no `<placeholders>`; icon URLs 200 | **Pass** |
| Upstream code reading: FFmpeg argv AST scan (29 lists, output last), email-validator 2.2.0 special-use list, uvicorn 0.34.2 socket API, FFmpeg n5.1.6 options | **Pass** |
| No `VOLUME`; `COPY --chmod=0755` into a new dir (Rule 8.22); every `curl` has `--retry 5 --retry-all-errors` | **Pass** |
| `docker build --platform linux/amd64` of the three services; running the stack | **Not run (unverified)** |
