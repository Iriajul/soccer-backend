"""admin.py — age_groups app."""
from django.contrib import admin

from .models import AgeGroup


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "id", "club_id", "coordinator_id", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "id"]
    ordering = ["-created_at"]
    raw_id_fields = ["club_id", "coordinator_id"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Age Group", {"fields": ("id", "name", "description")}),
        ("Assignment", {"fields": ("club_id", "coordinator_id")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
