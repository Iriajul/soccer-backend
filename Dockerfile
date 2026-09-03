# ═══════════════════════════════════════════════════════════════════════════
# Stage 1 — deps-builder: compile wheels from requirements.
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS deps-builder

WORKDIR /wheels

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt .
COPY requirements/production.txt .

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r production.txt

# ═══════════════════════════════════════════════════════════════════════════
# Stage 2 — runtime: minimal image, compiled wheels + app code only.
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django && \
    adduser --system --ingroup django --no-create-home django

COPY --from=deps-builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Runtime dirs (profile-image uploads live in /app/storage, served at /storage).
RUN mkdir -p /app/static /app/staticfiles /app/media /app/storage /app/logs && \
    chown -R django:django /app

COPY --chown=django:django docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# App code lives under src/ → copy its contents to /app so `config`/`apps`
# are importable and manage.py sits at /app/manage.py.
COPY --chown=django:django src/ /app/

USER django

EXPOSE 3000

ENTRYPOINT ["/entrypoint.sh"]
