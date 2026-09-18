from django.urls import path
from .api import HazardZoneAPI, IncidentProbabilityAPI

urlpatterns = [
    path('api/hazard-zones/', HazardZoneAPI.as_view(), name='hazard_zones'),
    path('api/incident-probability/', IncidentProbabilityAPI.as_view(), name='incident_probability'),
]
