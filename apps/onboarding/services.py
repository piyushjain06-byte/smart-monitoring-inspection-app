"""
Approving a SchemeApplication is the one moment where an applicant's
self-reported details become real platform rows: an NGO or Institute
(depending on applicant_type) plus a Project, all under the Scheme they
applied to. The applicant's own account is promoted into that NGO's
`admin_user` / Institute's `incharge` slot in the same step, so their
existing NGO-portal login immediately shows the new project — no extra
account linking needed (see apps.registry.portal_views for how that
scoping already reads NGO.admin_user / Institute.incharge).

Kept as a single transaction so a failure partway through never leaves,
say, a created NGO with no Project.
"""
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role
from apps.registry.models import Institute, NGO, Project

from .models import SchemeApplication


@transaction.atomic
def approve_application(application: SchemeApplication, reviewer, approved_fund_amount=None, review_notes=""):
    amount = approved_fund_amount if approved_fund_amount is not None else application.proposed_fund_amount
    applicant = application.applicant

    if application.applicant_type == SchemeApplication.ApplicantType.NGO:
        ngo = NGO.objects.create(
            scheme=application.scheme,
            name=application.organization_name,
            registration_number=application.registration_number,
            contact_person=application.contact_person,
            contact_phone=application.contact_phone,
            contact_email=application.contact_email,
            admin_user=applicant,
        )
        application.created_ngo = ngo
        applicant.role = Role.NGO_ADMIN
    else:
        institute = Institute.objects.create(
            scheme=application.scheme,
            name=application.organization_name,
            address=application.address,
            state=application.state,
            district=application.district,
            latitude=application.latitude,
            longitude=application.longitude,
            incharge=applicant,
        )
        application.created_institute = institute
        applicant.role = Role.PROJECT_INCHARGE

    applicant.save(update_fields=["role"])

    project = Project.objects.create(
        scheme=application.scheme,
        name=application.project_name,
        start_date=application.proposed_start_date,
        end_date=application.proposed_end_date,
        sanctioned_budget=amount,
        is_active=True,
    )
    application.created_project = project

    application.approved_fund_amount = amount
    application.status = SchemeApplication.Status.APPROVED
    application.review_notes = review_notes
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()

    return application


def reject_application(application: SchemeApplication, reviewer, review_notes=""):
    application.status = SchemeApplication.Status.REJECTED
    application.review_notes = review_notes
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save()
    return application
