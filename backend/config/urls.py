"""
URL configuration for IntZam LMS project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/', include('apps.loans.urls')),
    path('api/v1/', include('apps.accounting.urls')),
    path('api/v1/', include('apps.reports.urls')),
    path('api/v1/', include('apps.ai.urls')),
    path('', include('apps.website.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
