"""
Shared DRF permission classes, used across apps.registry and apps.inspections
so "who counts as an official vs. a field officer" is defined in exactly one
place instead of being re-implemented per view.
"""
from rest_framework.permissions import BasePermission

OFFICIAL_ROLES = {"SUPER_ADMIN", "STATE_AUTHORITY", "DISTRICT_AUTHORITY"}
FIELD_ROLES = {"INSPECTION_OFFICER", "PMU_TEAM"}


def is_official(user):
    """
    True for anyone who should see the government dashboard: the three
    authority roles, plus Django is_staff/is_superuser (covers the
    createsuperuser account, which may not have `role` set to SUPER_ADMIN).
    """
    if not user or not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser or getattr(user, "role", None) in OFFICIAL_ROLES


class IsOfficial(BasePermission):
    """Restricts a view to dashboard-side roles (District/State/Super Admin)."""
    message = "This is only available to government officials."

    def has_permission(self, request, view):
        return is_official(request.user)
