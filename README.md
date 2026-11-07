# Deploy and Host PRINTFILM with Railway

PRINTFILM is an open-source (MIT) studio for AI short videos and AI short dramas: it turns a topic or a script into a storyboard, generates the shot images and video clips, and composes the final cut with FFmpeg. This community template runs PRINTFILM v0.3.0 with its API, user web app, admin console, PostgreSQL and Redis.

## About Hosting PRINTFILM

PRINTFILM is a FastAPI backend with an in-process task runtime (scheduler, executor and poller, no separate worker), a React user app and a React admin console. Text, image, video and voice generation go through one provider, TokenFree: upstream's open-source build is wired to its gateway. Upstream publishes only `latest`-style images, so this template builds the v0.3.0 release from source, verified by checksum. Media is stored on a Railway volume, and the admin login is created for you with a generated password. Sign-up is closed by default.

## Common Use Cases

- Turn product selling points into short marketing videos from 20+ built-in style templates
- Write a short drama from a one-line idea: outline, script, characters, scenes, storyboard, episodes
- Generate single images or clips without the full pipeline (text-to-image, image-to-video and other tools)
- Give a small team one shared studio, with the provider key and usage managed in the admin console
- Offer generation to your own apps through PRINTFILM's open API (`/api/v1`, per-user API keys)

## Dependencies for PRINTFILM Hosting

- PRINTFILM v0.3.0 API, user app and admin console (built from the upstream release by this template)
- PostgreSQL 18 and Redis 8 (included)
- A Railway volume for generated media (included)
- A TokenFree account and API key to generate anything (optional at deploy, can be added later)

### Deployment Dependencies

- PRINTFILM source and releases: https://github.com/yi1108/printfilm
- PRINTFILM v0.3.0 release notes: https://github.com/yi1108/printfilm/releases/tag/v0.3.0
- TokenFree (keys, balance, price list): https://www.tokenfree.com
- Caddy: https://caddyserver.com/docs/

### Implementation Details

| Service | Built from | Role | Public |
|---|---|---|---|
| Web | upstream `frontend/` + Caddy 2.11 | User app; forwards `/api` and `/static` to the API | yes |
| Admin | upstream `admin/` + Caddy 2.11 | Admin console (admin accounts only) | yes |
| API | upstream `backend/` on Python 3.12 + FFmpeg | API, task runtime, video composing; volume `/app/static/generated` | no |
| Postgres | Railway PostgreSQL 18 | Users, projects, tasks, settings | no |
| Redis | Redis 8.2 | Live progress events, password-reset tokens | no |

**First login and first video**

1. Wait until all services are Active. The first build compiles both web apps and installs the API's packages, so it takes several minutes.
2. Open the **Admin** URL and sign in with `ADMIN_EMAIL` (default `admin@example.com`) and `ADMIN_PASSWORD` from the **API** service variables.
3. If you did not enter `TOKENFREE_API_KEY` at deploy: System settings → Models, paste your TokenFree key and save. Default models are Kimi K2.6 (text), Seedream 5.0 Pro (images) and Seedance 2.5 (video with built-in voice-over).
4. Open the **Web** URL and sign in with the same login. Go to AI Short Video, start a project, pick a style template and enter your topic. Choose the full pipeline (images, video clips, final cut) or images with text (stills only, faster and cheaper).
5. Review the storyboard, generate images, then clips, then the final cut. Jobs keep running if you leave the page; results appear in History.

**Language.** The user app switches between Chinese and English for navigation and the main pages, but much of the studio, the drama workspace and the server messages are Chinese only. The admin console is Chinese only. Built-in templates and prompts are written in Chinese, and scripts come out in Chinese unless you write your own.

**Access.** Only Web and Admin are public. The admin console works only for admin accounts. Upstream lets anyone register and every account generates on your TokenFree key, so this template closes sign-up. To let others in, set `PRINTFILM_SIGNUP_ENABLED=true` on the API and redeploy. Consider turning billing on in the admin console, so each account spends only the balance you grant. `ADMIN_PASSWORD` is applied on every deploy, so change it there rather than in the app. Keep `SECRET_KEY` as it is: changing it signs everyone out and makes the saved TokenFree key unreadable.

**Media.** Upstream supports Aliyun OSS only, not S3, so media lives on the volume and is served under `/static/` on the Web domain. Like upstream, anyone with a media link can open it, and parts of the paths are predictable. Seedance must download reference images over public HTTPS. With OSS off, the template hands it `https://{web-domain}/static/...` links (`PRINTFILM_PUBLIC_MEDIA_URLS`), so video from uploaded or older images works.

**Settings after the first start.** `PUBLIC_BASE_URL`, the models and the TokenFree key are imported once, then managed in the admin console. After adding a custom domain to Web, update the site address under System settings. A `TOKENFREE_API_KEY` added later is stored only while no key is saved.

**What it costs**

- Railway: about $5–6/month idle and $12–20/month for a small team making a few videos a week (RAM, CPU, volumes). Composing uses up to the CPU cap (`PRINTFILM_FFMPEG_THREADS`, auto = the service's CPU limit, at most 8).
- Minimum plan: Hobby. The API needs about 300–700 MB of RAM and more while FFmpeg composes long videos. Trial's 1 GB per service and small volume are enough to try the app, not for regular video work. Media over 5 GB needs Pro.
- TokenFree bills generation separately. At its public price list on 2026-11-07: Seedream 5.0 Pro about $0.06–0.12 per image, Seedance 2.5 about $0.14 per second at 480p and $0.32 at 720p. A 30-second 480p short with six shots therefore costs roughly $4–5. Prices change; check TokenFree before large jobs.

**Email.** Password-reset and cost-alert e-mails need SMTP (admin console). Railway allows outbound SMTP on Pro only.

**Scaling.** Keep the API at one replica: the task runtime runs in the process, and the volume belongs to one service. Give it more RAM and CPU for long episodes. Web and Admin are stateless. Generation runs at TokenFree, so Railway usage stays small.

**Pinning and upgrading.** The release is pinned in the three Dockerfiles under `services/` (commit and SHA-256 of the source tarball). Base images are pinned by digest. To upgrade, change the commit and checksum in all three, compare upstream's Dockerfiles and `deploy/.env.docker.example`, and redeploy. The schema upgrades itself at start; back up Postgres and the volume first.

The bundled Help, Contact and legal pages are upstream's and name printfilm.com. This is a community template, not made, endorsed or supported by the PRINTFILM authors or TokenFree. PRINTFILM's code runs unmodified.

### Why Deploy PRINTFILM on Railway?

Railway gives PRINTFILM HTTPS addresses for the studio and the admin console, a private network for the API and databases, persistent media storage and usage-based billing, without a server to maintain. You pay Railway for the small server footprint; the heavy image and video generation runs at TokenFree.
