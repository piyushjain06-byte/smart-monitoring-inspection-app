from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/registry/", include("apps.registry.urls")),
    path("api/inspections/", include("apps.inspections.urls")),
    # JWT — used by the React dashboard + inspector web app (Part 7 of the plan)
    path("api/auth/login/", TokenObtainPairView.as_view(), name="jwt-login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),
    # Legacy token auth — kept for the mobile submit.html fallback page
    path("api-token-auth/", obtain_auth_token),
]

# Serve uploaded evidence files (photos/videos) in local dev.
# In production this is handled by the web server/S3, not Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
