"""admin.py — connections app."""
from django.contrib import admin
from django.utils.html import format_html

from .models import ConnectionRequest

_STATUS_COLORS = {
    "PENDING": "#f59e0b",
    "WAITING_ON_PARENT": "#0891b2",
    "WAITING_ON_CHILD": "#0891b2",
    "APPROVED": "#10b981",
    "REJECTED": "#ef4444",
}


@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "parent_id", "child_id", "club_id", "status_badge", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["id"]
    ordering = ["-created_at"]
    raw_id_fields = ["requester_id", "parent_id", "child_id", "club_id"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Request", {"fields": ("id", "requester_id", "parent_id", "child_id", "club_id")}),
        ("Status", {"fields": ("status",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def status_badge(self, obj):
        color = _STATUS_COLORS.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{}</span>',
            color, obj.status,
        )
    status_badge.short_description = "Status"
