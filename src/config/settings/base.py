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
    "jazzmin",  # must precede django.contrib.admin
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
    # WhiteNoise serves /static/ (Jazzmin admin assets) straight from gunicorn,
    # so the admin is styled without any nginx /static/ rule. Must sit right
    # after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CSRF is required by the Django/Jazzmin admin's login + change forms.
    # It does NOT affect the JWT API: every DRF APIView is csrf_exempt by
    # default (we use only JWT auth, never SessionAuthentication), so API
    # clients are unaffected. The root hello view is csrf_exempt too.
    "django.middleware.csrf.CsrfViewMiddleware",
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
# WhiteNoise storage: compressed, no manifest (manifest is strict and 500s if
# any referenced asset is missing — the admin's own CSS occasionally references
# optional files, so we avoid the manifest variant).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ── CSRF / proxy (for the admin behind nginx over HTTPS) ────────────────────────
# Django must trust the HTTPS origin for admin form POSTs, and must know the
# request is HTTPS (nginx terminates TLS and forwards X-Forwarded-Proto).
CSRF_TRUSTED_ORIGINS = [
    f"https://{h}" for h in ALLOWED_HOSTS if h not in ("127.0.0.1", "localhost", "*")
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MEDIA_URL = "/media/"
MEDIA_ROOT = MEDIA_DIR

# Uploaded profile images live here and are served at /storage/<file>,
# exactly like the NestJS ServeStaticModule mount.
STORAGE_URL = "/storage/"
STORAGE_ROOT = STORAGE_DIR

# ── CORS (NestJS enableCors() = all origins) ─────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Jazzmin admin UI (styled to match the Athlon-go admin) ──────────────────────
JAZZMIN_SETTINGS = {
    "site_title": "Soccer Club Admin",
    "site_header": "Soccer Club",
    "site_brand": "Soccer Club",
    "site_logo": "images/favicon.png",
    "login_logo": "images/favicon.png",
    "site_icon": "images/favicon.png",
    "site_logo_classes": "img-circle",
    "welcome_sign": "Welcome to Soccer Club Admin",
    "copyright": "Soccer Club",
    "search_model": ["users.User", "clubs.Club"],
    "topmenu_links": [{"name": "Home", "url": "admin:index"}],
    "show_sidebar": True,
    "navigation_expanded": True,
    "related_modal_active": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.Group": "fas fa-users",
        "users.User": "fas fa-user",
        "clubs.Club": "fas fa-shield-alt",
        "age_groups.AgeGroup": "fas fa-layer-group",
        "teams.Team": "fas fa-futbol",
        "events.Event": "fas fa-calendar-day",
        "performance.Performance": "fas fa-chart-line",
        "connections.ConnectionRequest": "fas fa-link",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "use_google_fonts_cdn": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "lux",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-outline-primary",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}
