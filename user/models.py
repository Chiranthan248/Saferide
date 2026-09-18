from django.db import models
from django.contrib.auth.models import User


class Commuter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    emergency_contact = models.CharField(max_length=15)
    address = models.TextField()
    # Note: email is accessed via user.email (no redundant field)

    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Commuters"

    def __str__(self):
        return self.user.username


class RideDetails(models.Model):
    commuter = models.ForeignKey(Commuter, on_delete=models.CASCADE, related_name='rides')
    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)  # Bus, Auto, Cab, etc.
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)  # Set when ride ends
    is_active = models.BooleanField(default=True)  # Trip in progress
    
    # Live Tracking Fields
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Ride Details"
        indexes = [
            models.Index(fields=['commuter', 'is_active'], name='idx_ride_commuter_active'),
            models.Index(fields=['start_time'], name='idx_ride_start_time'),
            models.Index(fields=['is_active'], name='idx_ride_active'),
        ]

    def __str__(self):
        return f"{self.commuter.user.username} - {self.vehicle_number}"


class SOSRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
        ('Resolved', 'Resolved'),
    ]
    
    ride = models.ForeignKey(RideDetails, on_delete=models.CASCADE, related_name='sos_requests')
    guardian = models.ForeignKey('admin_app.Guardian', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=100)  # Can use GeoDjango later
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "SOS Request"
        verbose_name_plural = "SOS Requests"
        indexes = [
            models.Index(fields=['status'], name='idx_sos_status'),
            models.Index(fields=['timestamp'], name='idx_sos_timestamp'),
        ]

    def __str__(self):
        return f"SOS by {self.ride.commuter.user.username} at {self.timestamp}"


class IncidentReport(models.Model):
    INCIDENT_TYPES = [
        ('Harassment', 'Harassment'),
        ('Theft', 'Theft'),
        ('Suspicious Activity', 'Suspicious Activity'),
        ('Unsafe Route', 'Unsafe Route'),
        ('Other', 'Other')
    ]
    
    commuter = models.ForeignKey(Commuter, on_delete=models.CASCADE, related_name='incidents')
    ride = models.ForeignKey(RideDetails, on_delete=models.SET_NULL, null=True, blank=True)
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES)
    description = models.TextField()
    lat = models.FloatField()
    lng = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Incident Reports"
        indexes = [
            models.Index(fields=['lat', 'lng'], name='idx_incident_coords'),
            models.Index(fields=['timestamp'], name='idx_incident_timestamp'),
        ]

    def __str__(self):
        return f"{self.incident_type} reported by {self.commuter.user.username} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class TrustedContact(models.Model):
    """Emergency contacts a commuter can manage (up to 3)."""
    RELATIONSHIP_CHOICES = [
        ('Parent', 'Parent'),
        ('Spouse', 'Spouse'),
        ('Sibling', 'Sibling'),
        ('Friend', 'Friend'),
        ('Other', 'Other'),
    ]

    commuter = models.ForeignKey(Commuter, on_delete=models.CASCADE, related_name='trusted_contacts')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='Other')

    class Meta:
        verbose_name_plural = "Trusted Contacts"

    def __str__(self):
        return f"{self.name} ({self.relationship}) — {self.commuter.user.username}"