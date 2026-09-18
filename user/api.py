import logging

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.exceptions import ValidationError

from .models import Commuter, RideDetails, SOSRequest, IncidentReport
from .serializers import CommuterSerializer, RideDetailsSerializer, SOSRequestSerializer, IncidentReportSerializer
from utils import validate_coordinates

logger = logging.getLogger(__name__)


class RideDetailsViewSet(viewsets.ModelViewSet):
    """
    API endpoint for ride details.
    Users can only see and modify their own rides.
    """
    serializer_class = RideDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            commuter = Commuter.objects.get(user=self.request.user)
            return RideDetails.objects.filter(commuter=commuter).order_by('-start_time')
        except Commuter.DoesNotExist:
            return RideDetails.objects.none()

    def perform_create(self, serializer):
        commuter, _ = Commuter.objects.get_or_create(
            user=self.request.user,
            defaults={
                'phone': '0000000000',
                'emergency_contact': '0000000000',
                'address': 'Not specified',
            },
        )
        serializer.save(commuter=commuter)

    @action(detail=True, methods=['patch'])
    def location(self, request, pk=None):
        ride = self.get_object()
        lat_raw = request.data.get('lat')
        lng_raw = request.data.get('lng')

        if lat_raw is None or lng_raw is None:
            return Response(
                {'error': 'lat and lng are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat, lng = validate_coordinates(lat_raw, lng_raw)
        except ValidationError as e:
            return Response(
                {'error': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ride.current_lat = lat
        ride.current_lng = lng
        ride.save(update_fields=['current_lat', 'current_lng', 'last_updated'])
        return Response({'status': 'location updated'})


class SOSRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for SOS requests.
    Users can only see SOS requests linked to their own rides.
    """
    serializer_class = SOSRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            commuter = Commuter.objects.get(user=self.request.user)
            return SOSRequest.objects.filter(
                ride__commuter=commuter,
            ).select_related('ride').order_by('-timestamp')
        except Commuter.DoesNotExist:
            return SOSRequest.objects.none()

    def perform_create(self, serializer):
        """Create SOS alerts only for the authenticated user's active ride."""
        commuter, _ = Commuter.objects.get_or_create(
            user=self.request.user,
            defaults={
                'phone': '0000000000',
                'emergency_contact': '0000000000',
                'address': 'Not specified',
            },
        )
        ride = RideDetails.objects.filter(
            commuter=commuter, is_active=True,
        ).order_by('-start_time').first()
        if ride is None:
            raise ValidationError('An active ride is required to create an SOS request.')
        serializer.save(ride=ride)


class IncidentReportViewSet(viewsets.ModelViewSet):
    """
    API endpoint for incident reports.
    Users can only see their own incident reports.
    """
    serializer_class = IncidentReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            commuter = Commuter.objects.get(user=self.request.user)
            return IncidentReport.objects.filter(
                commuter=commuter,
            ).order_by('-timestamp')
        except Commuter.DoesNotExist:
            return IncidentReport.objects.none()

    def perform_create(self, serializer):
        commuter, _ = Commuter.objects.get_or_create(
            user=self.request.user,
            defaults={
                'phone': '0000000000',
                'emergency_contact': '0000000000',
                'address': 'Not specified',
            },
        )
        active_ride = RideDetails.objects.filter(
            commuter=commuter, is_active=True,
        ).order_by('-start_time').first()
        serializer.save(commuter=commuter, ride=active_ride)
