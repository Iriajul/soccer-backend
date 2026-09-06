from django.contrib import admin

from .models import ConnectionRequest


@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_id", "child_id", "club_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("id",)
    readonly_fields = ("id", "created_at", "updated_at")
