from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from user.api import RideDetailsViewSet, SOSRequestViewSet, IncidentReportViewSet

router = DefaultRouter()
router.register(r'ride', RideDetailsViewSet, basename='ridedetails')
router.register(r'sos', SOSRequestViewSet, basename='sosrequest')
router.register(r'incident', IncidentReportViewSet, basename='incidentreport')

urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin panel
    path('api/', include(router.urls)),
    path('analytics/', include('analytics_app.urls')),
    path('', include('user.urls')),   # User app (commuters)
    path('guardian/', include('admin_app.urls')),  # Admin/Guardian app
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)