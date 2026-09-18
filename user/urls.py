from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('start-ride/', views.start_ride, name='start_ride'),
    path('end-ride/', views.end_ride, name='end_ride'),
    path('trip-history/', views.trip_history, name='trip_history'),
    path('trigger-sos/', views.trigger_sos, name='trigger_sos'),
    path('update-location/', views.update_location, name='update_location'),
    path('report-incident/', views.report_incident, name='report_incident'),
    path('sos-status/<int:sos_id>/', views.sos_status_by_id, name='sos_status'),
    path('sos-status/', views.sos_status_latest, name='sos_status_latest'),
    path('contacts/', views.manage_contacts, name='manage_contacts'),

    path('profile/', views.profile, name='profile'),
    path('logout/', views.user_logout, name='logout'),
    path('', views.home, name='home'),
]