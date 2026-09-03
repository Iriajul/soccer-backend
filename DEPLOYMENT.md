# Deployment — co-hosted on the Hostinger VPS (behind the existing nginx)

Same automation model as Athlon-go: **Dockerfile → docker-compose → GitHub
Actions (`.github/workflows/deploy.yml`) → VPS over SSH**, triggered by
`./ship.sh "msg"` (push to `main`).

This app brings **no nginx of its own**. It runs `web` + `db` and plugs into the
**existing Athlon-go nginx** (which already owns ports 80/443 + SSL) as a new
subdomain. `docker-compose.prod.yml` puts `web` on that shared network with the
alias `soccer-api`.

---

## A. One-time VPS setup

1. **DNS** — add an A record for your subdomain (e.g. `soccer-api.athlongoapp.com`) → VPS IP.

2. **Clone the repo** on the VPS (pick a dir, e.g. `/home/zed/soccer-backend`):
   ```bash
   git clone https://github.com/Iriajul/soccer-backend.git /home/zed/soccer-backend
   ```

3. **Find the shared nginx network + container name:**
   ```bash
   docker network ls          # e.g. athlon-go_athlongo_network
   docker ps                  # e.g. athlon-go-nginx-1
   ```

4. **Add to the existing nginx config** (`Athlon-go/nginx/nginx.conf`):
   ```nginx
   upstream soccer_backend { server soccer-api:3000; }

   server {
       listen 443 ssl;
       server_name soccer-api.athlongoapp.com;                       # <-- your subdomain

       ssl_certificate     /etc/letsencrypt/live/soccer-api.athlongoapp.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/soccer-api.athlongoapp.com/privkey.pem;
       ssl_protocols TLSv1.2 TLSv1.3;
       client_max_body_size 10M;                             # profile-image uploads

       location / {
           proxy_pass          http://soccer_backend;
           proxy_set_header    Host              $host;
           proxy_set_header    X-Real-IP         $remote_addr;
           proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
           proxy_set_header    X-Forwarded-Proto $scheme;
           proxy_http_version  1.1;
       }
   }
   ```
   Also add the subdomain to the existing **HTTP→HTTPS redirect** `server_name`
   line so certbot can verify it.

5. **Issue the certificate** (your usual certbot flow), then restart the nginx
   container so it loads the new block.

---

## B. GitHub repo secrets (Settings → Secrets and variables → Actions)

| Secret | Example / note |
|---|---|
| `VPS_HOST` | VPS IP |
| `VPS_USER` | ssh user (e.g. `zed`) |
| `VPS_SSH_KEY` | private key with VPS access |
| `VPS_PORT` | ssh port (e.g. `22`) |
| `VPS_APP_DIR` | where you cloned it, e.g. `/home/zed/soccer-backend` |
| `NGINX_CONTAINER` | the existing nginx container, e.g. `athlon-go-nginx-1` |
| `PROXY_NETWORK` | shared nginx network, e.g. `athlon-go_athlongo_network` |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `ALLOWED_HOSTS` | `soccer-api.athlongoapp.com` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | this app's own DB creds |
| `JWT_ACCESS_SECRET` / `JWT_REFRESH_SECRET` | `openssl rand -hex 32` each |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USER` / `EMAIL_PASSWORD` | real SMTP |
| `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` | initial admin (only used if no admin exists) |

---

## C. Deploy

```bash
./ship.sh "your message"      # commits + pushes main → CI tests → deploys
```

The workflow: runs the Django test suite → SSH to the VPS → `git pull` → writes
`.env` from secrets → `docker compose -f docker-compose.prod.yml up -d --build`
(entrypoint runs `migrate` + `bootstrap_superadmin` + gunicorn) → reloads nginx.

---

## D. One-time data migration (existing Mongo → this Postgres)

Run **once**, into the fresh DB, before real traffic:

```bash
cd $VPS_APP_DIR
# NOTE: --entrypoint python bypasses the gunicorn entrypoint so the mgmt
# command actually runs. The prod Mongo DB is "test" (append it to the URI).
docker compose -f docker-compose.prod.yml run --rm \
  -e MONGODB_URI="<your production mongo URI>/test" \
  --entrypoint python soccerweb manage.py migrate_from_mongo --flush
```

Preserves every `_id`, keeps bcrypt logins working, and is safe to re-run
(idempotent). See `docs/MIGRATION_VALIDATION_REPORT.md`.

---

## E. Verify + hand off

```bash
curl https://soccer-api.athlongoapp.com/                 # -> Hello World!
```

Give the app/frontend teams the base URL **`https://soccer-api.athlongoapp.com`** — no
`/api` prefix, no trailing path. No client code changes; only the URL differs
from the NestJS backend.
