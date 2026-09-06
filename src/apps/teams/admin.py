from django.contrib import admin

from .models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "club_id", "age_group_id", "coach_id", "created_at")
    search_fields = ("name", "id")
    readonly_fields = ("id", "created_at", "updated_at")
