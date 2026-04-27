from django.db import models
from django.contrib.auth.models import User

class Guardian(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    organization = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)
    location = models.CharField(max_length=100)  # Can be updated via GPS

    def __str__(self):
        return f"{self.user.username} (Guardian)"

class GuardianResponse(models.Model):
    sos_request = models.ForeignKey('user.SOSRequest', on_delete=models.CASCADE)
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE)
    response_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Accepted', 'Accepted'), ('Rejected', 'Rejected')])

    def __str__(self):
        return f"{self.guardian.user.username} → {self.sos_request}"