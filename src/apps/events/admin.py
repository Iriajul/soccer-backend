"""admin.py — events app."""
from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "team_id", "club_id", "created_by", "created_at"]
    list_filter = ["date", "created_at"]
    search_fields = ["title", "description", "id"]
    ordering = ["-date"]
    raw_id_fields = ["team_id", "club_id", "created_by"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Event", {"fields": ("id", "title", "description", "date")}),
        ("Links", {"fields": ("team_id", "club_id", "created_by")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
