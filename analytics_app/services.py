import logging

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from django.core.cache import cache

from user.models import IncidentReport, RideDetails

logger = logging.getLogger(__name__)

# Cache key and timeout for the trained ML model
_MODEL_CACHE_KEY = 'analytics:incident_model'
_MODEL_CACHE_TIMEOUT = 3600  # 1 hour


class AnalyticsService:
    """Data science pipeline for hazard detection and incident prediction."""

    # ──────────────────────────────────────────────────────────
    # Data Ingestion
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def get_incident_data():
        incidents = IncidentReport.objects.all().values(
            'id', 'lat', 'lng', 'incident_type', 'timestamp', 'ride_id',
        )
        if not incidents:
            return pd.DataFrame()
        return pd.DataFrame(list(incidents))

    @staticmethod
    def get_ride_data():
        rides = RideDetails.objects.all().values(
            'id', 'vehicle_type', 'start_time', 'current_lat', 'current_lng',
        )
        if not rides:
            return pd.DataFrame()
        return pd.DataFrame(list(rides))

    # ──────────────────────────────────────────────────────────
    # K-Means Clustering — Hazard Zone Detection
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def identify_hazard_zones(n_clusters=5):
        df = AnalyticsService.get_incident_data()
        if df.empty or len(df) < n_clusters:
            return []

        X = df[['lat', 'lng']]
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(X)
        
        centers = kmeans.cluster_centers_
        hazard_zones = []
        for i, center in enumerate(centers):
            cluster_incidents = df[df['cluster'] == i]
            hazard_zones.append({
                'id': i,
                'lat': center[0],
                'lng': center[1],
                'incident_count': len(cluster_incidents),
                'risk_level': (
                    'High' if len(cluster_incidents) > 10
                    else ('Medium' if len(cluster_incidents) > 5 else 'Low')
                ),
            })
        
        return hazard_zones

    # ──────────────────────────────────────────────────────────
    # Logistic Regression — Incident Probability
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def train_regression_model():
        """
        Train a binary Logistic Regression classifier.

        Positive class (1): incident locations/times.
        Negative class (0): ride locations/times that had NO linked incident.
        """
        incidents = AnalyticsService.get_incident_data()
        rides = AnalyticsService.get_ride_data()
        
        if incidents.empty or rides.empty:
            return None

        # Collect ride IDs that had incidents to avoid data leakage
        incident_ride_ids = set(
            incidents['ride_id'].dropna().astype(int).tolist()
        )

        data = []

        # Positive samples: incidents
        for _, row in incidents.iterrows():
            hour = row['timestamp'].hour
            data.append([hour, row['lat'], row['lng'], 1])

        # Negative samples: rides WITHOUT an incident
        for _, row in rides.iterrows():
            if pd.notna(row['current_lat']) and pd.notna(row['current_lng']):
                if row['id'] not in incident_ride_ids:
                    hour = row['start_time'].hour
                    data.append([hour, row['current_lat'], row['current_lng'], 0])
                
        if len(data) < 2:
            return None

        df = pd.DataFrame(data, columns=['hour', 'lat', 'lng', 'target'])

        # Need both classes to train a classifier
        if df['target'].nunique() < 2:
            return None
        
        X = df[['hour', 'lat', 'lng']]
        y = df['target']
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = LogisticRegression(max_iter=200)
        model.fit(X_scaled, y)

        logger.info(
            "Model trained: %d samples (%d incidents, %d safe rides)",
            len(df), int(y.sum()), int((1 - y).sum()),
        )
        
        return model, scaler

    @staticmethod
    def get_cached_model():
        """
        Return the trained model from cache, or train and cache it.
        Avoids retraining on every API request.
        """
        model_data = cache.get(_MODEL_CACHE_KEY)
        if model_data is None:
            logger.info("ML model cache miss — training new model")
            model_data = AnalyticsService.train_regression_model()
            if model_data is not None:
                cache.set(_MODEL_CACHE_KEY, model_data, _MODEL_CACHE_TIMEOUT)
        return model_data

    @staticmethod
    def invalidate_model_cache():
        """Call this after new incidents are added to force retraining."""
        cache.delete(_MODEL_CACHE_KEY)
        logger.info("ML model cache invalidated")

    @staticmethod
    def predict_incident_probability(model, scaler, hour, lat, lng):
        if not model or not scaler:
            return 0.0
            
        X_input = pd.DataFrame([[hour, lat, lng]], columns=['hour', 'lat', 'lng'])
        X_scaled = scaler.transform(X_input)
        
        prob = model.predict_proba(X_scaled)[0][1]  # Probability of target=1
        return round(prob * 100, 2)
