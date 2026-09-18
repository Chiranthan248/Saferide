import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.core.exceptions import ValidationError

from .services import AnalyticsService
from utils import validate_coordinates

logger = logging.getLogger(__name__)


class HazardZoneAPI(APIView):
    """Return K-Means clustered hazard zones from incident data."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        zones = AnalyticsService.identify_hazard_zones(n_clusters=3)
        return Response(zones)


class IncidentProbabilityAPI(APIView):
    """Predict incident probability for a given location and hour."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ── Validate & parse parameters ──────────────────────────
        lat_raw = request.query_params.get('lat', '28.6139')
        lng_raw = request.query_params.get('lng', '77.2090')
        hour_raw = request.query_params.get('hour', '22')

        try:
            lat, lng = validate_coordinates(lat_raw, lng_raw)
        except ValidationError as e:
            return Response(
                {'error': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            hour = int(hour_raw)
            if not (0 <= hour <= 23):
                raise ValueError("Hour out of range")
        except (TypeError, ValueError):
            return Response(
                {'error': 'hour must be an integer between 0 and 23.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Predict ──────────────────────────────────────────────
        model_data = AnalyticsService.get_cached_model()
        if not model_data:
            return Response({'probability': 0, 'risk_level': 'Low'})

        model, scaler = model_data
        prob = AnalyticsService.predict_incident_probability(model, scaler, hour, lat, lng)

        if prob > 60:
            risk = 'High'
        elif prob > 30:
            risk = 'Medium'
        else:
            risk = 'Low'

        return Response({'probability': prob, 'risk_level': risk})
