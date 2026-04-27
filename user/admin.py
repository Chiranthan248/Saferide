from django.contrib import admin
from .models import Commuter, RideDetails, SOSRequest

admin.site.register(Commuter)
admin.site.register(RideDetails)
admin.site.register(SOSRequest)
