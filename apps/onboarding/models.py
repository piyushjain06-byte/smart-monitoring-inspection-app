"""
PS 26095 onboarding flow (per the plan's own diagram):

    GOVERNMENT -> Creates Schemes -> Scheme Catalogue
        -> NGO / Institute / Project apply/propose
        -> Government Review -> APPROVED / REJECTED
        -> (if approved) Scheme Allotted -> Monitoring begins

`SchemeApplication` is the "apply/propose" + "Government Review" step.
It is deliberately its own table, separate from apps.registry's NGO/
Institute/Project models — an application is a *request*, not yet a real
platform row. Only once a Super Admin approves it does
apps.onboarding.services.approve_application() actually create the NGO or
Institute (+ Project) rows that the rest of the platform (CCTV, attendance,
inspections, AI risk engine) operates on.
"""
from django.conf import settings
from django.db import models


class SchemeApplication(models.Model):

    class ApplicantType(models.TextChoices):
        NGO = "NGO", "NGO"
        INSTITUTE = "INSTITUTE", "Institute"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scheme_applications",
    )
    applicant_type = models.CharField(max_length=20, choices=ApplicantType.choices)
    scheme = models.ForeignKey("registry.Scheme", on_delete=models.CASCADE, related_name="applications")

    # --- Org details: become the NGO or Institute row on approval ---
    organization_name = models.CharField(max_length=255)
    registration_number = models.CharField(
        max_length=100, blank=True,
        help_text="NGO registration number — required for NGO applications.",
    )
    contact_person = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    contact_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # --- Proposal: becomes the Project row on approval ---
    project_name = models.CharField(max_length=255)
    project_plan = models.TextField()
    proposed_fund_amount = models.DecimalField(max_digits=14, decimal_places=2)
    proposed_start_date = models.DateField(null=True, blank=True)
    proposed_end_date = models.DateField(null=True, blank=True)

    # --- Government review ---
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    review_notes = models.TextField(blank=True, help_text="Government's notes/reason — shown to the applicant.")
    approved_fund_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Government can adjust the sanctioned amount on approval; defaults to the amount requested.",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # --- Filled in once approved — the rows this application produced ---
    created_ngo = models.ForeignKey("registry.NGO", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_institute = models.ForeignKey("registry.Institute", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_project = models.ForeignKey("registry.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization_name} -> {self.scheme.name} ({self.status})"
