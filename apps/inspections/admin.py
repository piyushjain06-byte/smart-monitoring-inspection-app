from django.contrib import admin

from .models import (
    Evidence,
    InspectionAssignment,
    InspectionField,
    InspectionReport,
    InspectionTemplate,
)


class InspectionFieldInline(admin.TabularInline):
    """
    Lets you add/edit checklist questions directly on the Template page
    instead of navigating to a separate screen — this is the "checklist
    builder" UI for now (Part 4.6), no custom frontend needed yet.
    """
    model = InspectionField
    extra = 1


@admin.register(InspectionTemplate)
class InspectionTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    inlines = [InspectionFieldInline]


@admin.register(InspectionAssignment)
class InspectionAssignmentAdmin(admin.ModelAdmin):
    list_display = ("institute", "officer", "template", "due_date", "status", "assigned_at")
    list_filter = ("status", "template")
    search_fields = ("institute__name", "officer__username")


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0


@admin.register(InspectionReport)
class InspectionReportAdmin(admin.ModelAdmin):
    list_display = ("assignment", "submitted_at", "location_verified", "overall_score")
    list_filter = ("location_verified",)
    inlines = [EvidenceInline]


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("report", "media_type", "captured_at")
    list_filter = ("media_type",)
