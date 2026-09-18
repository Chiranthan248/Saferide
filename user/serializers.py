from rest_framework import serializers
from .models import Commuter, RideDetails, SOSRequest, IncidentReport

class CommuterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Commuter
        fields = ['id', 'username', 'phone', 'emergency_contact', 'is_verified']

class RideDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideDetails
        fields = '__all__'
        read_only_fields = ['commuter', 'start_time', 'end_time', 'last_updated']

class SOSRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOSRequest
        fields = '__all__'
        # SOS records are created only for the caller's active ride; a
        # commuter must never be able to assign or impersonate a guardian.
        read_only_fields = ['ride', 'guardian', 'timestamp', 'status']

class IncidentReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentReport
        fields = '__all__'
        read_only_fields = ['commuter', 'ride', 'timestamp']
