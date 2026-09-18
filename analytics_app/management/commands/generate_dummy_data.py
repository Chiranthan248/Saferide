from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import Commuter, RideDetails, IncidentReport, SOSRequest
from django.utils import timezone
import random
import datetime

class Command(BaseCommand):
    help = 'Generates rich dummy data for commuters, rides, incidents, and SOS alerts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Clearing existing dummy data...')
        IncidentReport.objects.all().delete()
        SOSRequest.objects.all().delete()
        RideDetails.objects.all().delete()
        Commuter.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

        self.stdout.write('Creating commuters...')
        names = ['priya', 'sneha', 'kavya', 'ananya', 'divya', 'meera', 'riya', 'pooja', 'swati', 'neha']
        commuters = []
        for i, name in enumerate(names):
            user = User.objects.create_user(
                username=name,
                password='password123',
                first_name=name.capitalize(),
            )
            commuter = Commuter.objects.create(
                user=user,
                phone=f'9876543{i:03d}',
                emergency_contact=f'9123456{i:03d}',
                address=f'{i+1} MG Road, New Delhi',
                is_verified=True
            )
            commuters.append(commuter)
        self.stdout.write(self.style.SUCCESS(f'  [OK] {len(commuters)} commuters created'))

        # ── Geographic hotspots (3 real-ish Delhi clusters) ──────────
        base_lat = 28.6139
        base_lng = 77.2090
        hotspots = [
            (base_lat + 0.055, base_lng + 0.060),   # Connaught Place area
            (base_lat - 0.045, base_lng - 0.025),   # Nehru Place area
            (base_lat + 0.015, base_lng - 0.065),   # Dwarka area
        ]
        vehicle_types = ['Bus', 'Auto', 'Cab', 'Metro Feeder', 'E-Rickshaw']
        incident_types = ['Harassment', 'Theft', 'Suspicious Activity', 'Unsafe Route', 'Other']
        sources      = ['Connaught Place', 'Nehru Place', 'Dwarka', 'Saket', 'Lajpat Nagar', 'Karol Bagh']
        destinations = ['AIIMS', 'IGI Airport', 'Noida', 'Gurgaon', 'Rohini', 'Pitampura']

        self.stdout.write('Creating rides and incidents...')
        rides_created = 0
        incidents_created = 0
        sos_created = 0

        for i in range(120):
            commuter = random.choice(commuters)
            hs_lat, hs_lng = random.choice(hotspots)
            lat = hs_lat + random.uniform(-0.025, 0.025)
            lng = hs_lng + random.uniform(-0.025, 0.025)

            start_days_ago = random.randint(0, 45)
            start_time = timezone.now() - datetime.timedelta(
                days=start_days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )

            ride = RideDetails(
                commuter=commuter,
                vehicle_number=f'DL{random.randint(1,12):02d}C{random.randint(1000,9999)}',
                vehicle_type=random.choice(vehicle_types),
                source=random.choice(sources),
                destination=random.choice(destinations),
                current_lat=lat,
                current_lng=lng,
                is_active=False,
            )
            ride.save()
            # Override auto_now_add
            RideDetails.objects.filter(pk=ride.pk).update(start_time=start_time)
            rides_created += 1

            # ── Generate incident (30% chance) ──────────────────────
            if random.random() < 0.30:
                hour = random.choice([7, 8, 20, 21, 22, 23, 0, 1])
                inc_time = start_time.replace(hour=hour)

                inc = IncidentReport(
                    commuter=commuter,
                    ride=ride,
                    incident_type=random.choice(incident_types),
                    description=random.choice([
                        'Driver took an unknown route.',
                        'Another passenger behaving aggressively.',
                        'Driver asked inappropriate questions.',
                        'Felt followed after getting off.',
                        'Vehicle not matching app details.',
                        'Driver refused to stop at destination.',
                        'Suspicious activity near bus stop.',
                    ]),
                    lat=lat + random.uniform(-0.005, 0.005),
                    lng=lng + random.uniform(-0.005, 0.005),
                )
                inc.save()
                IncidentReport.objects.filter(pk=inc.pk).update(timestamp=inc_time)
                incidents_created += 1

            # ── Generate SOS (8% chance) ────────────────────────────
            if random.random() < 0.08:
                sos = SOSRequest(
                    ride=ride,
                    location=f'{lat:.4f}, {lng:.4f}',
                    status=random.choice(['Pending', 'Accepted', 'Resolved', 'Resolved']),
                    notes='Auto-generated SOS for demo purposes.',
                )
                sos.save()
                SOSRequest.objects.filter(pk=sos.pk).update(timestamp=start_time)
                sos_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'  [OK] {rides_created} rides, {incidents_created} incidents, {sos_created} SOS records'
        ))
        self.stdout.write(self.style.SUCCESS(
            '\nDummy data generation complete! Analytics pipeline is ready.\n'
            'Login credentials: username=priya (or sneha/kavya/etc.), password=password123'
        ))
