from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "date", "team_id", "club_id", "created_by")
    search_fields = ("title", "id")
    readonly_fields = ("id", "created_at", "updated_at")
