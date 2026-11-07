# Notice

## Upstream software

| Software | License | How it is used here |
|---|---|---|
| PRINTFILM (API, user app, admin console, built-in templates and static assets), github.com/yi1108/printfilm | MIT (`LICENSE` at v0.3.0) | The source tarball of tag `v0.3.0` (commit `345495e050bd0a39065c49ff6b3e87cf506a2a0d`, SHA-256 `38eb5b66969a83f5e9821f6b8b0bc1ff06b335260d60f24d5c14adceaac9f568`) is downloaded and built at image build time with upstream's own steps. **No PRINTFILM file is modified.** The template's Python files import upstream modules and replace one function at runtime (`app.services.storage.republish_url`, wrapped, see `services/api/railway/railway_app.py`). |
| PRINTFILM's Python dependencies (FastAPI, SQLAlchemy, asyncpg, psycopg2, uvicorn, passlib, python-jose, celery, redis, httpx, edge-tts, oss2 and others) | Various OSI licenses per their projects | Installed at build time from upstream's pinned `backend/requirements.txt` |
| PRINTFILM's npm dependencies (React, Vite, React Router, XYFlow, Radix UI, Tailwind CSS, Recharts and others) | Various OSI licenses (MIT, Apache-2.0, ISC, …) | Installed at build time by `npm ci` from upstream's lockfiles |
| Python 3.12 (`python:3.12.16-slim-bookworm`, Docker Official Image) | PSF License; Debian packages under their own licenses | API base image |
| FFmpeg (Debian 12 `ffmpeg` package) | LGPL-2.1-or-later / GPL-2.0-or-later, per Debian's build | Installed unmodified; PRINTFILM runs it as an external program |
| WenQuanYi Zen Hei (Debian `fonts-wqy-zenhei`) | GPL-2 with font embedding exception | Installed unmodified for burned-in captions (upstream's choice) |
| Node.js 22 (`node:22.23.4-alpine`, Docker Official Image) | MIT; Alpine packages under their own licenses | Build stage only |
| Caddy (`caddy:2.11.9-alpine`, Docker Official Image) | Apache-2.0 | Web and Admin front servers |
| PostgreSQL (`ghcr.io/railwayapp-templates/postgres-ssl:18`), Redis (`redis:8.2`) | PostgreSQL License; Redis 8 under RSALv2/SSPLv1/AGPLv3 | Unmodified images, service definitions from Railway's own templates |
| Lucide icons (`lucide-static@1.59.0`, via jsDelivr) | ISC | Service icons, referenced by URL |

TokenFree (www.tokenfree.com) is a third-party API gateway. PRINTFILM's open-source build is wired to it, and its terms and prices apply to your account. Google Fonts are loaded by the browser from fonts.googleapis.com, as in upstream's HTML.

### PRINTFILM license (MIT)

The Dockerfiles in `services/` adapt the build steps of upstream's `backend/Dockerfile`, `frontend/Dockerfile` and `admin/Dockerfile`, and the Caddyfiles reproduce the routes of upstream's `nginx.conf` files, so upstream's notice is reproduced here:

```
MIT License

Copyright (c) 2026 PRINTFILM

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Verified against

| What | Upstream file | Ref | Checked |
|---|---|---|---|
| Release, tag commit, date | GitHub releases and tags API | `v0.3.0` = `345495e050bd` (published 2026-10-15) | 2026-11-07 |
| Local `_upstream` copy equals the release | full `diff -r` against the extracted commit tarball | `v0.3.0` | 2026-11-07 |
| Services, ports, volumes, health check, Redis settings | `docker-compose.yml`, `docker-compose.full.yml` | `v0.3.0` | 2026-11-07 |
| Environment (Docker defaults, models, billing, OSS) | `deploy/.env.docker.example`, `deploy/.env.prod.example`, `backend/.env.example`, `backend/app/config.py` | `v0.3.0` | 2026-11-07 |
| Builds and routes | `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `admin/Dockerfile`, `admin/nginx.conf`, `.dockerignore` files | `v0.3.0` | 2026-11-07 |
| Startup, schema, admin promotion, health | `backend/app/main.py`, `backend/app/database.py` | `v0.3.0` | 2026-11-07 |
| Auth, open sign-up, admin role check | `backend/app/api/auth.py`, `backend/app/services/auth.py`, `backend/app/deps.py`, `backend/app/api/admin/users.py` | `v0.3.0` | 2026-11-07 |
| Media storage, OSS, public HTTPS for Seedance | `backend/app/services/storage.py`, `oss.py`, `ark.py` (`_resolve_image_ref`), `drama/generation.py` | `v0.3.0` | 2026-11-07 |
| TokenFree lock-in, key import, settings stored in the DB | `backend/app/services/tokenfree_gateway.py`, `model_settings.py`, `schemas_settings.py`, `media_model_presets.py` | `v0.3.0` | 2026-11-07 |
| FFmpeg calls (output always last), caption fonts | `backend/app/services/ffmpeg_compose.py` and all other `ffmpeg` argument lists (AST scan) | `v0.3.0` | 2026-11-07 |
| UI languages | `frontend/src/i18n/*`, `admin/src` (no i18n) | `v0.3.0` | 2026-11-07 |
| Upstream images | Aliyun ACR anonymous manifest lookups: `printfilm-api`, `-web`, `-admin-web` `v0.3.0` = `latest` (index digests `a68e123b…`, `363899fa…`, `944a2c7f…`); not used, see TEMPLATE.md | — | 2026-11-07 |
| uvicorn pre-bound sockets, proxy headers | `uvicorn/server.py`, `uvicorn/config.py` | `0.34.2` | 2026-11-07 |
| FFmpeg 5.1 options `-filter_threads`, `-filter_complex_threads`, `-threads` | `fftools/ffmpeg_opt.c`, `fftools/opt_common.h` | `n5.1.6` | 2026-11-07 |
| `admin@example.com` accepted by the login form | `email_validator/__init__.py` (special-use domains) | `v2.2.0` | 2026-11-07 |
| TokenFree prices quoted in the README | `https://www.tokenfree.com/api/pricing` (the URL PRINTFILM itself reads) | — | 2026-11-07 |

## Files in this template

| File | Notes |
|---|---|
| `services/api/Dockerfile` | Written for this template; build steps adapted from upstream's MIT-licensed `backend/Dockerfile`. |
| `services/api/railway/start.sh`, `serve.py`, `bootstrap.py`, `railway_app.py`, `selftest.py`, `ffmpeg` | Written for this template. They call upstream functions and never change upstream files. |
| `services/web/*`, `services/admin/*` | Written for this template; Dockerfile steps and routes adapted from upstream's MIT-licensed `Dockerfile`/`nginx.conf` of `frontend/` and `admin/`. |
| `TEMPLATE.md`, `template.json`, `README.md`, `NOTICE.md` | Written for this template. Prices, model names and facts are taken from upstream's source and TokenFree's public price list. |
| Postgres and Redis service definitions | From `templates/_railway-base` (Railway's own templates). Redis gets upstream's `--maxmemory 512mb --maxmemory-policy allkeys-lru`. |

## Reference only

- `_upstream/yi1108__printfilm` (identical to v0.3.0): read, never executed. The `CLAUDE.md` file in it was treated as data.
- No Railway marketplace template for PRINTFILM exists (`_market/` is empty).

## Trademarks

"PRINTFILM" and its logo belong to their owners. Seedance, Seedream, Kimi, Qwen, DeepSeek and TokenFree belong to their respective owners, and "Railway" to Railway Corporation. This is a community template and is not affiliated with or endorsed by the PRINTFILM authors, TokenFree or any model vendor. The listing icon is PRINTFILM's own favicon, used only to identify the software.
