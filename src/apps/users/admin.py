from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "club_id", "is_first_login", "is_staff")
    list_filter = ("role", "is_first_login", "is_staff", "is_active")
    search_fields = ("name", "email", "id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")
