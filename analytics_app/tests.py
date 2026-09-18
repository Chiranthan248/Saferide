from django.test import TestCase
from django.contrib.auth.models import User

from user.models import Commuter, RideDetails, IncidentReport
from .services import AnalyticsService


class HazardZoneTests(TestCase):
    """Tests for K-Means hazard zone detection."""

    def test_empty_data_returns_empty_list(self):
        """With no incidents, identify_hazard_zones should return []."""
        result = AnalyticsService.identify_hazard_zones(n_clusters=3)
        self.assertEqual(result, [])

    def test_fewer_than_n_clusters_returns_empty(self):
        """With fewer incidents than clusters requested, should return []."""
        user = User.objects.create_user(username='testuser', password='pass')
        commuter = Commuter.objects.create(
            user=user, phone='1234567890',
            emergency_contact='0987654321', address='Test',
        )
        # Create only 2 incidents but request 3 clusters
        for i in range(2):
            IncidentReport.objects.create(
                commuter=commuter,
                incident_type='Theft',
                description='Test incident',
                lat=28.6 + i * 0.01,
                lng=77.2 + i * 0.01,
            )

        result = AnalyticsService.identify_hazard_zones(n_clusters=3)
        self.assertEqual(result, [])


class RegressionModelTests(TestCase):
    """Tests for the logistic regression model training."""

    def test_empty_data_returns_none(self):
        """With no data, train_regression_model should return None."""
        result = AnalyticsService.train_regression_model()
        self.assertIsNone(result)

    def test_incidents_only_no_rides_returns_none(self):
        """With incidents but no rides, should return None."""
        user = User.objects.create_user(username='testuser', password='pass')
        commuter = Commuter.objects.create(
            user=user, phone='1234567890',
            emergency_contact='0987654321', address='Test',
        )
        IncidentReport.objects.create(
            commuter=commuter,
            incident_type='Harassment',
            description='Test',
            lat=28.6, lng=77.2,
        )

        result = AnalyticsService.train_regression_model()
        self.assertIsNone(result)
