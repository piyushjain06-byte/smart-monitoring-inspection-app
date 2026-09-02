"""
python manage.py audit_roles

Addresses the "role-scoping audit" item from README.md's next-steps list:
apps.core.permissions.is_official() treats ANY is_staff/is_superuser
account as an official regardless of its `role` field (kept that way on
purpose, for local/demo convenience — see the docstring on is_official()).

That fallback is invisible until it collides with a role that expects
different (narrower) treatment: an NGO_ADMIN or PROJECT_INCHARGE account
that also happens to have is_staff=True will be routed to the government
dashboard / official API scope instead of their own portal
(apps/registry/portal_views.py), and a field officer with is_staff=True
would bypass the field-officer-only "my own assignments" restriction too.

This command only REPORTS such conflicts — it does not change any account,
since flipping is_staff/is_superuser is a security-relevant decision a
human should make deliberately (e.g. from /admin/), not something a script
should silently "fix" on your production data.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.core.permissions import FIELD_ROLES, NGO_PORTAL_ROLES, OFFICIAL_ROLES

User = get_user_model()


class Command(BaseCommand):
    help = "Reports user accounts whose role and is_staff/is_superuser flags disagree."

    def handle(self, *args, **options):
        conflicts = 0
        notes = 0

        for user in User.objects.all().order_by("username"):
            role = user.role
            flags_say_official = user.is_staff or user.is_superuser

            if flags_say_official and role in NGO_PORTAL_ROLES:
                conflicts += 1
                self.stdout.write(self.style.WARNING(
                    f"[CONFLICT] {user.username}: is_staff/is_superuser=True but role={role!r} "
                    f"(NGO portal role) — is_official() will route this account to the "
                    f"government dashboard instead of the NGO/Incharge portal. "
                    f"If unintended, uncheck 'Staff status'/'Superuser status' in /admin/."
                ))
            elif flags_say_official and role in FIELD_ROLES:
                conflicts += 1
                self.stdout.write(self.style.WARNING(
                    f"[CONFLICT] {user.username}: is_staff/is_superuser=True but role={role!r} "
                    f"(field officer role) — is_official() will treat this account as an "
                    f"official, bypassing the 'only see my own assignments' restriction in "
                    f"InspectionAssignmentViewSet.get_queryset(). If unintended, uncheck "
                    f"'Staff status'/'Superuser status' in /admin/."
                ))
            elif not flags_say_official and role in OFFICIAL_ROLES:
                notes += 1
                self.stdout.write(
                    f"[NOTE] {user.username}: role={role!r} (official) but is_staff=False — "
                    f"this account authenticates fine against the API as an official, but "
                    f"cannot log into /admin/. Usually fine; flagging in case that's a surprise."
                )

        self.stdout.write("")
        if conflicts == 0 and notes == 0:
            self.stdout.write(self.style.SUCCESS("No role/flag conflicts found."))
        else:
            self.stdout.write(self.style.WARNING(
                f"{conflicts} conflict(s), {notes} note(s) — see above."
            ))
