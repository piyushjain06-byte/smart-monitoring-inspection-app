from django.contrib import admin

from .models import SchemeApplication


@admin.register(SchemeApplication)
class SchemeApplicationAdmin(admin.ModelAdmin):
    list_display = ("organization_name", "applicant_type", "scheme", "status", "proposed_fund_amount", "created_at")
    list_filter = ("status", "applicant_type", "scheme")
    search_fields = ("organization_name", "applicant__username")
    readonly_fields = ("created_at", "reviewed_at", "created_ngo", "created_institute", "created_project")
