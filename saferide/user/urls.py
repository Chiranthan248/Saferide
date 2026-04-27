from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),  # Add this line
    path('register/', views.register, name='register'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('start-ride/', views.start_ride, name='start_ride'),
    path('trigger-sos/', views.trigger_sos, name='trigger_sos'),
    path('update-location/', views.update_location, name='update_location'),
    path('sos-status/<int:sos_id>/', views.sos_status_by_id, name='sos_status'),
    path('sos-status/', views.sos_status_latest, name='sos_status_latest'),

    path('', views.home, name='home'),
]