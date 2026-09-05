"""
Shared DRF permission classes, used across apps.registry and apps.inspections
so "who counts as an official vs. a field officer" is defined in exactly one
place instead of being re-implemented per view.

Extended (post-Phase-3 work) with NGO_ADMIN / PROJECT_INCHARGE checks for
the NGO/Institute portal — see apps/registry/portal_views.py. These are
kept as separate helpers rather than folded into is_official()/IsOfficial,
since an NGO admin or project incharge should NOT see the government
dashboard's full cross-institute data — they get their own, narrower views.

Extended again for the onboarding/approval flow (PS 26095's own diagram:
"GOVERNMENT" reviews and approves/rejects NGO/Institute scheme
applications) with is_super_admin()/IsSuperAdmin — deliberately narrower
than is_official(), since District/State Authority can see the dashboard
but do NOT get to approve or reject applications; only the actual Super
Admin does.
"""
from rest_framework.permissions import BasePermission

OFFICIAL_ROLES = {"SUPER_ADMIN", "STATE_AUTHORITY", "DISTRICT_AUTHORITY"}
FIELD_ROLES = {"INSPECTION_OFFICER", "PMU_TEAM"}
NGO_PORTAL_ROLES = {"NGO_ADMIN", "PROJECT_INCHARGE"}


def is_official(user):
    """
    True for anyone who should see the government dashboard: the three
    authority roles, plus Django is_staff/is_superuser (covers the
    createsuperuser account, which may not have `role` set to SUPER_ADMIN).

    NOTE (role-scoping audit): the is_staff/is_superuser fallback below is
    intentionally permissive for local/demo convenience, but it means an
    NGO_ADMIN or PROJECT_INCHARGE account that also has is_staff=True (e.g.
    created by hand in /admin/) will be routed here instead of to their own
    portal. This is a config issue on individual accounts, not a bug in
    this function — run `python manage.py audit_roles` to find and fix any
    accounts where that's happened.
    """
    if not user or not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser or getattr(user, "role", None) in OFFICIAL_ROLES


def is_field_officer(user):
    """True for Inspection Officer / PMU Team accounts (mirrors frontend/src/constants/roles.js)."""
    if not user or not user.is_authenticated:
        return False
    return getattr(user, "role", None) in FIELD_ROLES and not is_official(user)


def is_ngo_admin(user):
    """True for NGO/Institute Admin accounts — see NGO.admin_user in apps.registry.models."""
    if not user or not user.is_authenticated:
        return False
    return getattr(user, "role", None) == "NGO_ADMIN"


def is_project_incharge(user):
    """True for Project Incharge accounts — see Institute.incharge in apps.registry.models."""
    if not user or not user.is_authenticated:
        return False
    return getattr(user, "role", None) == "PROJECT_INCHARGE"


def is_ngo_portal_user(user):
    """True for either NGO portal role, and not already an official (mirrors is_field_officer's shape)."""
    if not user or not user.is_authenticated:
        return False
    return getattr(user, "role", None) in NGO_PORTAL_ROLES and not is_official(user)


def is_super_admin(user):
    """
    True only for the actual government approver in the onboarding flow
    (PS 26095's diagram: "GOVERNMENT" == DoSJE HQ Super Admin). Deliberately
    narrower than is_official() — District/State Authority can view the
    dashboard but do NOT get to approve/reject scheme applications.
    """
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or getattr(user, "role", None) == "SUPER_ADMIN"


class IsOfficial(BasePermission):
    """Restricts a view to dashboard-side roles (District/State/Super Admin)."""
    message = "This is only available to government officials."

    def has_permission(self, request, view):
        return is_official(request.user)


class IsOfficialOrFieldOfficer(BasePermission):
    message = "This is only available to officials or field officers."

    def has_permission(self, request, view):
        return is_official(request.user) or is_field_officer(request.user)


class IsNGOOrIncharge(BasePermission):
    """Restricts a view to the NGO/Institute Admin or Project Incharge portal."""
    message = "This is only available to NGO admins or project incharges."

    def has_permission(self, request, view):
        return is_ngo_admin(request.user) or is_project_incharge(request.user)


class IsSuperAdmin(BasePermission):
    """Restricts a view/action to the government's Super Admin (see is_super_admin())."""
    message = "Only the DoSJE HQ Super Admin can approve or reject scheme applications."

    def has_permission(self, request, view):
        return is_super_admin(request.user)
