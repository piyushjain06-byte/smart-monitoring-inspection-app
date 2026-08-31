from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Extends Django's default UserAdmin so role/phone/state/district are
    editable straight from /admin/ — this IS your role-management UI
    for the local/demo phase, no custom frontend needed yet.
    """
    list_display = ("username", "get_full_name", "role", "state", "district", "is_active")
    list_filter = ("role", "state", "district", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Platform Role & Scope", {
            "fields": ("role", "phone_number", "preferred_language", "state", "district"),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Platform Role & Scope", {
            "fields": ("role", "phone_number", "state", "district"),
        }),
    )
