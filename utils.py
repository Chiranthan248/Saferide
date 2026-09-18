"""
Shared utility functions for the SafeRide project.
"""
from django.core.exceptions import ValidationError


def validate_coordinates(lat, lng):
    """
    Validate and return (lat, lng) as floats.
    Raises ValidationError if values are not valid geographic coordinates.
    """
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        raise ValidationError("Latitude and longitude must be numeric values.")

    if not (-90 <= lat <= 90):
        raise ValidationError(f"Latitude {lat} is out of range (-90 to 90).")
    if not (-180 <= lng <= 180):
        raise ValidationError(f"Longitude {lng} is out of range (-180 to 180).")

    return lat, lng
