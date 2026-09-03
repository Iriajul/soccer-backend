# Soccer Club Backend — Django (DRF) port

A **compatibility-preserving** re-implementation of the original NestJS + MongoDB
Soccer Club API, in Django + Django REST Framework on PostgreSQL.

> **Contract rule:** the external API is byte-compatible with the NestJS backend
> — same paths (no `/api` prefix), request/response shapes, status codes, error
> bodies, `_id` format, and documented quirks. The Flutter app and React admin
> switch only their base URL. See `../soccer_backend/PROJECT_DOCUMENTATION.md`.

## Layout

```
requirements/           base / development / production / test
docker/entrypoint.sh    migrate → bootstrap super admin → gunicorn (:3000)
Dockerfile              multi-stage build
docker-compose.dev.yml  local Postgres only (app runs on host)
docker-compose.yml      full stack (Postgres + app on :3000)
src/
  config/               settings (base/dev/prod/test), urls, wsgi/asgi
  common/               compatibility layer (ObjectId, NestJS errors, JWT,
                        auth principal, RolesGuard, roles/weights, bcrypt)
  apps/                 users, authentication, clubs, age_groups, teams,
                        events, performance, connections, dashboard
```

## Local development

```bash
python -m venv venv && ./venv/bin/pip install -r requirements/development.txt
cp .env.example src/.env            # then edit secrets
docker compose -f docker-compose.dev.yml up -d    # Postgres on host :5434
cd src
../venv/bin/python manage.py migrate
../venv/bin/python manage.py bootstrap_superadmin
../venv/bin/python manage.py runserver 3000
```

## Tests

```bash
cd src && DJANGO_SETTINGS_MODULE=config.settings.test ../venv/bin/python manage.py test
```

## Migrate existing Mongo data (one-time, ID-preserving)

```bash
cd src
MONGODB_URI="mongodb+srv://..." \
  ../venv/bin/python manage.py migrate_from_mongo   # add --flush to clear target first
```

Preserves every `_id` verbatim, prefixes bcrypt hashes so existing users log in
without resetting, and preserves `createdAt`/`updatedAt`.

## Deploy

```bash
# create a root .env with SECRET_KEY, JWT secrets, POSTGRES_*, SUPER_ADMIN_*, ALLOWED_HOSTS
docker compose up -d --build      # app on :3000
```

The entrypoint runs migrations, bootstraps the super admin (if none), collects
static, and serves via gunicorn. Point clients at `http://<host>:3000`.

## Notes / follow-ups

- Verify against the live NestJS backend with a golden-master diff before go-live.
- `SUPER_ADMIN_EMAIL` / `SUPER_ADMIN_PASSWORD` default to `admin@soccer.com` /
  `Admin123!` — override in production.
- JWT secrets should be ≥32 bytes in production.
