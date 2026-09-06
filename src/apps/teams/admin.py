"""admin.py — teams app."""
from django.contrib import admin

from .models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "id", "club_id", "age_group_id", "coach_id", "roster_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "id"]
    ordering = ["-created_at"]
    raw_id_fields = ["club_id", "age_group_id", "coach_id"]
    readonly_fields = ["id", "version", "created_at", "updated_at"]

    fieldsets = (
        ("Team", {"fields": ("id", "name")}),
        ("Assignment", {"fields": ("club_id", "age_group_id", "coach_id")}),
        ("Roster", {"fields": ("roster",)}),
        ("Meta", {"fields": ("version", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def roster_count(self, obj):
        return len(obj.roster or [])
    roster_count.short_description = "Players"
