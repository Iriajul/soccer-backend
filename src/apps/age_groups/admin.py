from django.contrib import admin

from .models import AgeGroup


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "club_id", "coordinator_id", "created_at")
    search_fields = ("name", "id")
    readonly_fields = ("id", "created_at", "updated_at")
