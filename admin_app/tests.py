from django.test import TestCase, Client
from django.contrib.auth.models import User
from user.models import Commuter, RideDetails, SOSRequest
from .models import Guardian


class GuardianAuthTests(TestCase):
    """Tests for Guardian authentication and dashboard access."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='guardian1', password='pass12345')
        self.guardian = Guardian.objects.create(
            user=self.user,
            phone='9876543210',
            organization='Control Room Central',
            location='Delhi',
        )

    def test_guardian_login_success(self):
        """Guardian with valid credentials should log in and redirect to guardian dashboard."""
        response = self.client.post('/guardian/login/', {
            'username': 'guardian1',
            'password': 'pass12345',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/guardian/dashboard/')

    def test_non_guardian_login_denied(self):
        """Regular user without Guardian model should not be allowed into guardian dashboard."""
        User.objects.create_user(username='commuter1', password='pass12345')
        response = self.client.post('/guardian/login/', {
            'username': 'commuter1',
            'password': 'pass12345',
        })
        self.assertEqual(response.status_code, 200)  # Re-renders login with error message
        self.assertContains(response, 'not registered as a guardian')

    def test_register_guardian_restricted_to_superusers(self):
        """Non-superuser should not be allowed to access or register guardians."""
        self.client.login(username='guardian1', password='pass12345')
        response = self.client.get('/guardian/register/')
        self.assertEqual(response.status_code, 302)  # Redirects to dashboard with error message


class GuardianSOSTests(TestCase):
    """Tests for Guardian SOS management (accept, decline, resolve)."""

    def setUp(self):
        self.client = Client()
        # Guardian user
        self.guardian_user = User.objects.create_user(username='guardian_user', password='pass12345')
        self.guardian = Guardian.objects.create(
            user=self.guardian_user,
            phone='9876543210',
            organization='SafeCity Ops',
            location='28.6139, 77.2090',
        )

        # Commuter + Ride + SOS
        self.commuter_user = User.objects.create_user(username='commuter_user', password='pass12345')
        self.commuter = Commuter.objects.create(
            user=self.commuter_user,
            phone='9999999999',
            emergency_contact='8888888888',
            address='Test City',
        )
        self.ride = RideDetails.objects.create(
            commuter=self.commuter,
            vehicle_number='DL01AB1234',
            vehicle_type='Auto',
            source='Origin',
            destination='Destination',
            is_active=True,
        )
        self.sos = SOSRequest.objects.create(
            ride=self.ride,
            location='28.6139, 77.2090',
            status='Pending',
        )

    def test_accept_sos(self):
        """Guardian accepting a pending SOS changes status to Accepted."""
        self.client.login(username='guardian_user', password='pass12345')
        response = self.client.post(f'/guardian/sos/{self.sos.id}/accept/')
        self.assertEqual(response.status_code, 302)

        self.sos.refresh_from_db()
        self.assertEqual(self.sos.status, 'Accepted')
        self.assertEqual(self.sos.guardian, self.guardian)

    def test_decline_sos(self):
        """Guardian declining a pending SOS changes status to Declined."""
        self.client.login(username='guardian_user', password='pass12345')
        response = self.client.post(f'/guardian/sos/{self.sos.id}/decline/')
        self.assertEqual(response.status_code, 302)

        self.sos.refresh_from_db()
        self.assertEqual(self.sos.status, 'Declined')

    def test_non_guardian_cannot_accept_sos(self):
        """A logged-in commuter cannot perform guardian-only SOS actions."""
        self.client.login(username='commuter_user', password='pass12345')
        response = self.client.post(f'/guardian/sos/{self.sos.id}/accept/')
        self.assertEqual(response.status_code, 302)
        self.sos.refresh_from_db()
        self.assertEqual(self.sos.status, 'Pending')

