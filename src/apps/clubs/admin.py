"""admin.py — clubs app."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Club


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ["name", "id", "active_badge", "created_at", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "id"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Club", {"fields": ("id", "name", "is_active")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def active_badge(self, obj):
        color = "#10b981" if obj.is_active else "#ef4444"
        label = "Active" if obj.is_active else "Inactive"
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{}</span>',
            color, label,
        )
    active_badge.short_description = "Status"
