from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/registry/", include("apps.registry.urls")),
    path("api/inspections/", include("apps.inspections.urls")),
    path("api-token-auth/", obtain_auth_token),
]

# Serve uploaded evidence files (photos/videos) in local dev.
# In production this is handled by the web server/S3, not Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
