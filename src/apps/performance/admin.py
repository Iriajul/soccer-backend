from django.contrib import admin

from .models import Performance


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ("id", "player_id", "club_id", "passing", "dribbling",
                    "shooting", "defense", "stamina", "recorded_by")
    search_fields = ("id", "player_id")
    readonly_fields = ("id", "created_at", "updated_at")
