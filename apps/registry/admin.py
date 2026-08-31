from django.contrib import admin

from .models import Beneficiary, Institute, NGO, Project, Scheme, Staff


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(NGO)
class NGOAdmin(admin.ModelAdmin):
    list_display = ("name", "registration_number", "contact_person", "contact_phone")
    search_fields = ("name", "registration_number")


@admin.register(Institute)
class InstituteAdmin(admin.ModelAdmin):
    """
    Plain admin for now — just type latitude/longitude in as numbers
    (e.g. from Google Maps: right-click a spot -> the numbers shown are lat, lon).
    A map-click widget comes back once we're on PostGIS (GISModelAdmin).
    """
    list_display = ("name", "ngo", "scheme", "district", "state", "latitude", "longitude", "is_active")
    list_filter = ("state", "district", "is_active", "scheme")
    search_fields = ("name", "district", "state")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "institute", "start_date", "end_date", "sanctioned_budget", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("full_name", "institute", "designation", "phone_number")
    search_fields = ("full_name",)


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "project", "phone_number", "enrolled_on")
    search_fields = ("full_name",)
