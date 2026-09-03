"""
Base settings for the Soccer Club backend (Django port of the NestJS API).

Structure/conventions mirror the Athlon-go project, BUT the external API
contract deliberately does NOT: there is no `/api` prefix and no
`{success, data}` envelope — see `config/urls.py` and
`common/exceptions.py`. The NestJS backend is the behavioral oracle.
"""
from pathlib import Path
from datetime import timedelta
import os
import environ

# BASE_DIR points to the `config/` folder; BASE_DIR.parent is `src/`.
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR.parent
TEMPLATE_DIR = os.path.join(SRC_DIR, "templates")
STATIC_DIR = os.path.join(SRC_DIR, "static")
MEDIA_DIR = os.path.join(SRC_DIR, "media")
# Profile images are served under /storage (mirrors NestJS ServeStaticModule).
STORAGE_DIR = os.path.join(SRC_DIR, "storage")

env = environ.Env()
environ.Env.read_env(env_file=os.path.join(SRC_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-key")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# NODE_ENV drives NestJS-parity branches (dev temp passwords, 500 error detail,
# console-vs-email invites). Kept as an explicit knob so the port matches.
NODE_ENV = env("NODE_ENV", default="development")

# ── Applications ──────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    "django_filters",

    "apps.users",
    "apps.authentication",
    "apps.clubs",
    "apps.age_groups",
    "apps.teams",
    "apps.events",
    "apps.performance",
    "apps.connections",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # NOTE: CSRF middleware intentionally omitted — the NestJS API is a
    # stateless JWT API with no CSRF protection; adding it would reject the
    # existing clients' requests.
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ───────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="soccer"),
        "USER": env("POSTGRES_USER", default="soccer"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="soccer"),
        "HOST": env("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# Custom user model — REQUIRED before the first migration.
AUTH_USER_MODEL = "users.User"

# ── Password hashing (COMPATIBILITY) ───────────────────────────────────────────
# The existing NestJS users have raw bcrypt hashes (bcrypt.hash(pw, 10)).
# `BCryptPasswordHasher` (NOT BCryptSHA256) verifies those exactly.
# It is listed first so migrated hashes validate on the first login attempt.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = []  # NestJS enforces no strength rules; match that.

# ── DRF ─────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "common.authentication.JWTAccessAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    # NestJS returns raw payloads / plain arrays — NEVER a paginated envelope.
    "DEFAULT_PAGINATION_CLASS": None,
    # Custom handler reproduces the NestJS {statusCode, message, error} shape.
    "EXCEPTION_HANDLER": "common.exceptions.nest_exception_handler",
    "UNAUTHENTICATED_USER": None,
}

# ── JWT (mirror NestJS exactly) ─────────────────────────────────────────────────
JWT_ACCESS_SECRET = env("JWT_ACCESS_SECRET", default="access-secret")
JWT_REFRESH_SECRET = env("JWT_REFRESH_SECRET", default="refresh-secret")
JWT_ACCESS_EXPIRES_IN = env("JWT_ACCESS_EXPIRES_IN", default="30d")
JWT_REFRESH_EXPIRES_IN = env("JWT_REFRESH_EXPIRES_IN", default="60d")

# ── Email (nodemailer-compatible SMTP) ──────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_PASSWORD", default="")
EMAIL_USE_TLS = False  # NestJS uses secure:false on non-465 ports.

# ── Super admin bootstrap (mirrors UsersService.onModuleInit) ───────────────────
SUPER_ADMIN_EMAIL = env("SUPER_ADMIN_EMAIL", default="admin@soccer.com")
SUPER_ADMIN_PASSWORD = env("SUPER_ADMIN_PASSWORD", default="Admin123!")

# ── i18n / tz ────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static / media / storage ─────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(SRC_DIR, "staticfiles")
STATICFILES_DIRS = [STATIC_DIR] if os.path.isdir(STATIC_DIR) else []

MEDIA_URL = "/media/"
MEDIA_ROOT = MEDIA_DIR

# Uploaded profile images live here and are served at /storage/<file>,
# exactly like the NestJS ServeStaticModule mount.
STORAGE_URL = "/storage/"
STORAGE_ROOT = STORAGE_DIR

# ── CORS (NestJS enableCors() = all origins) ─────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
