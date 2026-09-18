from django.contrib import admin
from .models import Commuter, RideDetails, SOSRequest, IncidentReport, TrustedContact

admin.site.register(Commuter)
admin.site.register(RideDetails)
admin.site.register(SOSRequest)
admin.site.register(IncidentReport)
admin.site.register(TrustedContact)
