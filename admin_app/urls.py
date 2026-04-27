# admin_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.guardian_login, name='guardian_login'),
    path('logout/', views.guardian_logout, name='guardian_logout'),
    path('dashboard/', views.guardian_dashboard, name='guardian_dashboard'),
    path('register/', views.register_guardian, name='register_guardian'),
    path('profile/', views.user_profile, name='user_profile'),
    
    # SOS related URLs
    path('sos/<int:sos_id>/details/', views.sos_details, name='sos_details'),
    path('sos/<int:sos_id>/accept/', views.accept_sos, name='accept_sos'),
    path('sos/<int:sos_id>/decline/', views.decline_sos, name='decline_sos'),
    path('sos/<int:sos_id>/resolve/', views.resolve_sos, name='resolve_sos'),
]