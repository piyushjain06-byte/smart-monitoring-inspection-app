from django.contrib import admin

from .models import Camera


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ("name", "institute", "camera_index", "stream_url", "status", "last_online", "is_active")
    list_filter = ("is_active", "institute")
    search_fields = ("name", "institute__name")
    readonly_fields = ("last_online",)
