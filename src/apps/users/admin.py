"""admin.py — production-grade admin for the users app (with password management)."""
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from common.roles import UserRole
from .models import User

_ROLE_COLORS = {
    "SUPER_ADMIN": "#7c3aed",
    "CLUB_OWNER": "#2563eb",
    "TECH_DIRECTOR": "#0891b2",
    "COORDINATOR": "#0d9488",
    "COACH": "#16a34a",
    "PLAYER": "#f59e0b",
    "PARENT": "#6b7280",
}


class UserCreationForm(forms.ModelForm):
    """Add-user form with two password fields (hashed with bcrypt on save)."""
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "name", "role", "club_id")

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two password fields didn't match.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # bcrypt (PASSWORD_HASHERS)
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Edit form — password shown as a hash with a link to the change form."""
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=_(
            "Raw passwords are not stored, so there is no way to see this user's "
            'password, but you can change it using <a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ["email", "name", "role_badge", "club_id", "is_first_login", "is_staff", "is_active", "created_at"]
    list_filter = ["role", "is_first_login", "is_staff", "is_active", "created_at"]
    search_fields = ["email", "name", "id"]
    ordering = ["-created_at"]
    raw_id_fields = ["club_id"]
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ["id", "last_login", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal info"), {"fields": ("name", "profile_image")}),
        (_("Role & Club"), {"fields": ("role", "club_id", "is_first_login")}),
        (_("Parent/Child links"), {"fields": ("child_player_ids", "parent_ids"), "classes": ("collapse",)}),
        (_("Admin access"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"), "classes": ("collapse",)}),
        (_("Timestamps"), {"fields": ("last_login", "created_at", "updated_at"), "classes": ("collapse",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "role", "club_id", "password1", "password2"),
        }),
    )

    def role_badge(self, obj):
        color = _ROLE_COLORS.get(obj.role, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:12px">{}</span>',
            color, obj.role,
        )
    role_badge.short_description = "Role"
