"""
Root URL configuration.

CONTRACT: routes hang directly off the server root — there is NO `/api` or
`/api/v1` prefix (unlike the Athlon-go template this project's structure is
modeled on). Paths must match the NestJS backend exactly, e.g.:

    GET  /
    POST /auth/login
    GET  /users/me
    GET  /teams
    GET  /events/team/<teamId>
    ...

Each app's urls.py declares its own full prefix (e.g. "auth/login"), so they
are all included at the empty path.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve

from common.views import root_hello

urlpatterns = [
    path("", root_hello, name="root-hello"),        # GET /  (public hello)
    path("django-admin/", admin.site.urls),         # not part of the API contract

    path("", include("apps.authentication.urls")),  # /auth/*
    path("", include("apps.users.urls")),           # /users/*
    path("", include("apps.clubs.urls")),           # /clubs/*
    path("", include("apps.age_groups.urls")),      # /age-groups/*
    path("", include("apps.teams.urls")),           # /teams/*
    path("", include("apps.events.urls")),          # /events/*
    path("", include("apps.performance.urls")),     # /performance/*
    path("", include("apps.connections.urls")),     # /connections/*
    path("", include("apps.dashboard.urls")),       # /dashboard/*

    # Uploaded profile images, served at /storage/<filename> (mirrors the
    # NestJS ServeStaticModule mount). Enabled in all environments because the
    # existing clients load images from this path.
    path(
        "storage/<path:path>",
        serve,
        {"document_root": settings.STORAGE_ROOT},
        name="storage",
    ),
]
