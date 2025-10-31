from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView  # For home page

urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin panel
    path('', include('user.urls')),   # User app (commuters)
    path('guardian/', include('admin_app.urls')),  # Admin/Guardian app
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)