import json

from django.test import TestCase, Client
from django.contrib.auth.models import User

from .models import Commuter, RideDetails, SOSRequest, IncidentReport


class SOSTests(TestCase):
    """Tests for SOS trigger functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.commuter = Commuter.objects.create(
            user=self.user,
            phone='9876543210',
            emergency_contact='9123456789',
            address='Test Address',
        )

    def test_sos_trigger_no_active_ride_returns_error(self):
        """SOS should fail gracefully when no ride is active."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            '/trigger-sos/',
            data=json.dumps({'location': '28.6139, 77.2090'}),
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('No active ride', data['message'])

    def test_sos_trigger_with_active_ride_succeeds(self):
        """SOS should succeed when a ride is active."""
        self.client.login(username='testuser', password='testpass123')

        RideDetails.objects.create(
            commuter=self.commuter,
            vehicle_number='DL01C1234',
            vehicle_type='Cab',
            source='Connaught Place',
            destination='AIIMS',
            is_active=True,
        )

        response = self.client.post(
            '/trigger-sos/',
            data=json.dumps({'location': '28.6139, 77.2090'}),
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('sos_id', data)

        # Verify SOS was actually created in DB
        self.assertEqual(SOSRequest.objects.count(), 1)
        sos = SOSRequest.objects.first()
        self.assertEqual(sos.status, 'Pending')


class APIAuthTests(TestCase):
    """Tests verifying that API endpoints require authentication."""

    def test_unauthenticated_ride_api_returns_403(self):
        """Unauthenticated users should not access the ride API."""
        response = self.client.get('/api/ride/')
        self.assertIn(response.status_code, [401, 403])

    def test_unauthenticated_sos_api_returns_403(self):
        """Unauthenticated users should not access the SOS API."""
        response = self.client.get('/api/sos/')
        self.assertIn(response.status_code, [401, 403])

    def test_unauthenticated_incident_api_returns_403(self):
        """Unauthenticated users should not access the incident API."""
        response = self.client.get('/api/incident/')
        self.assertIn(response.status_code, [401, 403])

    def test_incident_api_ignores_supplied_commuter(self):
        """Authenticated clients cannot file an incident under another commuter."""
        owner = User.objects.create_user(username='owner', password='testpass123')
        other = User.objects.create_user(username='other', password='testpass123')
        owner_commuter = Commuter.objects.create(
            user=owner, phone='9876543210', emergency_contact='9123456789', address='Owner address',
        )
        other_commuter = Commuter.objects.create(
            user=other, phone='9876543211', emergency_contact='9123456788', address='Other address',
        )
        self.client.login(username='owner', password='testpass123')
        response = self.client.post('/api/incident/', {
            'commuter': other_commuter.id,
            'incident_type': 'Theft',
            'description': 'Test report',
            'lat': 28.6139,
            'lng': 77.2090,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(IncidentReport.objects.get().commuter, owner_commuter)


class LocationValidationTests(TestCase):
    """Tests for coordinate validation in location updates."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.commuter = Commuter.objects.create(
            user=self.user,
            phone='9876543210',
            emergency_contact='9123456789',
            address='Test Address',
        )
        self.ride = RideDetails.objects.create(
            commuter=self.commuter,
            vehicle_number='DL01C1234',
            vehicle_type='Cab',
            source='Test Source',
            destination='Test Dest',
            is_active=True,
        )

    def test_valid_location_update_succeeds(self):
        """Valid lat/lng should update successfully."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            '/update-location/',
            data=json.dumps({'lat': 28.6139, 'lng': 77.2090}),
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['status'], 'success')

        self.ride.refresh_from_db()
        self.assertAlmostEqual(self.ride.current_lat, 28.6139, places=4)

    def test_invalid_lat_returns_error(self):
        """Out-of-range latitude should return validation error."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            '/update-location/',
            data=json.dumps({'lat': 999, 'lng': 77.2090}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_non_numeric_coords_returns_error(self):
        """Non-numeric coordinates should return validation error."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            '/update-location/',
            data=json.dumps({'lat': 'abc', 'lng': 77.2090}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class RegistrationTests(TestCase):
    """Tests for user registration."""

    def test_duplicate_username_fails(self):
        """Registration with an existing username should show an error."""
        User.objects.create_user(username='existing', password='pass12345')
        response = self.client.post('/register/', {
            'username': 'existing',
            'email': 'test@test.com',
            'password': 'newpass123',
            'password2': 'newpass123',
            'phone': '9876543210',
            'emergency_contact': '9123456789',
            'address': 'Some Address',
        })
        self.assertEqual(response.status_code, 200)  # Re-renders form
        self.assertContains(response, 'Username already exists')

    def test_successful_registration_redirects(self):
        """Valid registration should create user + commuter and redirect."""
        response = self.client.post('/register/', {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'securepass123',
            'password2': 'securepass123',
            'phone': '9876543210',
            'emergency_contact': '9123456789',
            'address': 'New Address',
        })
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(Commuter.objects.filter(user__username='newuser').exists())

    def test_duplicate_email_fails(self):
        User.objects.create_user(username='existing', email='same@example.com', password='pass12345')
        response = self.client.post('/register/', {
            'username': 'different', 'email': 'SAME@example.com',
            'password': 'securepass123', 'password2': 'securepass123',
            'phone': '9876543210', 'emergency_contact': '9123456789', 'address': 'Some Address',
        })
        self.assertContains(response, 'account with this email already exists')


class ProfileTests(TestCase):
    """Tests for profile updates."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.commuter = Commuter.objects.create(
            user=self.user,
            phone='0000000000',
            emergency_contact='0000000000',
            address='Old Address',
        )

    def test_profile_update_persists(self):
        """Profile changes should be saved to the database."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/profile/', {
            'first_name': 'Priya',
            'last_name': 'Sharma',
            'phone': '9876543210',
            'emergency_contact': '9123456789',
            'address': 'Updated Address',
        })
        self.assertEqual(response.status_code, 302)  # Redirect

        self.commuter.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.commuter.phone, '9876543210')
        self.assertEqual(self.commuter.address, 'Updated Address')
        self.assertEqual(self.user.first_name, 'Priya')
