from django.db import models
from django.contrib.auth.models import User

class Commuter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    emergency_contact = models.CharField(max_length=15)
    address = models.TextField()
    email = models.EmailField(null=True, blank=True)

    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class RideDetails(models.Model):
    commuter = models.ForeignKey(Commuter, on_delete=models.CASCADE)
    vehicle_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)  # Bus, Auto, Cab, etc.
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    start_time = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # Trip in progress

    def __str__(self):
        return f"{self.commuter.user.username} - {self.vehicle_number}"

class SOSRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Resolved', 'Resolved'),
    ]
    
    ride = models.ForeignKey(RideDetails, on_delete=models.CASCADE)
    guardian = models.ForeignKey('admin_app.Guardian', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=100)  # Can use GeoDjango later
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"SOS by {self.ride.commuter.user.username} at {self.timestamp}"