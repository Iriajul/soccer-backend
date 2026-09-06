"""admin.py — performance app."""
from django.contrib import admin

from .models import Performance


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ["player_id", "overall", "passing", "dribbling", "shooting",
                    "defense", "stamina", "recorded_by", "updated_at"]
    search_fields = ["id", "player_id"]
    ordering = ["-updated_at"]
    raw_id_fields = ["player_id", "club_id", "recorded_by"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("Player", {"fields": ("id", "player_id", "club_id")}),
        ("Ratings (0–100)", {"fields": ("passing", "dribbling", "shooting", "defense", "stamina")}),
        ("Meta", {"fields": ("recorded_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def overall(self, obj):
        import math
        total = obj.passing + obj.dribbling + obj.shooting + obj.defense + obj.stamina
        return int(math.floor(total / 5 + 0.5))
    overall.short_description = "Overall"
