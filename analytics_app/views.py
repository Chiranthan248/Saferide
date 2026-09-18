# analytics_app/views.py
#
# All analytics logic is served via the REST API in api.py.
# This module intentionally contains no HTML views.
# See analytics_app/api.py and analytics_app/urls.py for the API endpoints:
#   GET /analytics/api/hazard-zones/          → HazardZoneAPI
#   GET /analytics/api/incident-probability/  → IncidentProbabilityAPI
