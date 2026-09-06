"""admin.py — production-grade admin for the users app."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import User

_ROLE_COLORS = {
    "SUPER_ADMIN": "#7c3aed",
    "CLUB_OWNER": "#2563eb",
    "TECH_DIRECTOR": "#0891b2",
    "COORDINATOR": "#0d9488",
    "COACH": "#16a34a",
    "PLAYER": "#f59e0b",
    "PARENT": "#6b7280",
}


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "name", "role_badge", "club_id", "is_first_login", "is_staff", "is_active", "created_at"]
    list_filter = ["role", "is_first_login", "is_staff", "is_active", "created_at"]
    search_fields = ["email", "name", "id"]
    ordering = ["-created_at"]
    raw_id_fields = ["club_id"]
    # password shown but read-only here — change passwords via POST /auth/change-password
    # (or the app's reset flow) so they are always bcrypt-hashed correctly.
    readonly_fields = ["id", "password", "last_login", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal info"), {"fields": ("name", "profile_image")}),
        (_("Role & Club"), {"fields": ("role", "club_id", "is_first_login")}),
        (_("Parent/Child links"), {"fields": ("child_player_ids", "parent_ids"), "classes": ("collapse",)}),
        (_("Admin access"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"), "classes": ("collapse",)}),
        (_("Timestamps"), {"fields": ("last_login", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def role_badge(self, obj):
        color = _ROLE_COLORS.get(obj.role, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{}</span>',
            color, obj.role,
        )
    role_badge.short_description = "Role"
