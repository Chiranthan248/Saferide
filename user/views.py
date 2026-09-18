import json
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count

from .models import Commuter, RideDetails, SOSRequest, IncidentReport, TrustedContact
from utils import validate_coordinates

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Helper: get or auto-create commuter profile
# ──────────────────────────────────────────────────────────────

def _get_or_create_commuter(user):
    """Return the Commuter for *user*, auto-creating one if missing."""
    commuter, created = Commuter.objects.get_or_create(
        user=user,
        defaults={
            'phone': '0000000000',
            'emergency_contact': '0000000000',
            'address': 'Not specified',
        },
    )
    if created:
        logger.info("Auto-created commuter profile for user=%s", user.username)
    return commuter


# ──────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'user/login.html')


def user_logout(request):
    logout(request)
    return redirect('home')


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        phone = request.POST.get('phone', '').strip()
        emergency_contact = request.POST.get('emergency_contact', '').strip()
        address = request.POST.get('address', '').strip()

        # P2.13: Password confirmation
        if password != password2:
            return render(request, 'user/register.html', {'error': 'Passwords do not match.'})

        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'user/register.html', {'error': 'Enter a valid email address.'})

        if User.objects.filter(email__iexact=email).exists():
            return render(request, 'user/register.html', {'error': 'An account with this email already exists.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'user/register.html', {'error': 'Username already exists'})

        candidate = User(username=username, email=email)
        try:
            validate_password(password, user=candidate)
        except ValidationError as error:
            return render(request, 'user/register.html', {'error': ' '.join(error.messages)})

        user = User.objects.create_user(username=username, email=email, password=password)

        Commuter.objects.create(
            user=user,
            phone=phone,
            emergency_contact=emergency_contact,
            address=address,
        )
        logger.info("New commuter registered: %s", username)
        messages.success(request, 'Account created successfully! Please sign in.')
        return redirect('login')

    return render(request, 'user/register.html')


# ──────────────────────────────────────────────────────────────
# Profile
# ──────────────────────────────────────────────────────────────

@login_required
def profile(request):
    commuter = _get_or_create_commuter(request.user)
    
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        commuter.phone = request.POST.get('phone', '')
        commuter.emergency_contact = request.POST.get('emergency_contact', '')
        commuter.address = request.POST.get('address', '')
        commuter.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
        
    return render(request, 'user/profile.html', {'commuter': commuter})


# ──────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────

@login_required
def user_dashboard(request):
    commuter = _get_or_create_commuter(request.user)
    active_ride = RideDetails.objects.filter(commuter=commuter, is_active=True).first()
    trusted_contacts = TrustedContact.objects.filter(commuter=commuter)
    return render(request, 'user/dashboard.html', {
        'active_ride': active_ride,
        'commuter': commuter,
        'trusted_contacts': trusted_contacts,
    })


# ──────────────────────────────────────────────────────────────
# Rides
# ──────────────────────────────────────────────────────────────

@login_required
def start_ride(request):
    commuter = _get_or_create_commuter(request.user)
        
    if request.method == 'POST':
        # Deactivate all previous rides for this commuter
        RideDetails.objects.filter(commuter=commuter, is_active=True).update(
            is_active=False, end_time=timezone.now(),
        )
        
        vehicle_number = request.POST.get('vehicle_number', 'Unknown')
        vehicle_type = request.POST.get('vehicle_type', 'Unknown')
        source = request.POST.get('source', '')
        destination = request.POST.get('destination', '')

        new_ride = RideDetails.objects.create(
            commuter=commuter,
            vehicle_number=vehicle_number,
            vehicle_type=vehicle_type,
            source=source,
            destination=destination,
            is_active=True,
        )
        
        logger.info(
            "Ride started: id=%s user=%s route=%s→%s",
            new_ride.id, request.user.username, source, destination,
        )
        
        return redirect('user_dashboard')
        
    return render(request, 'user/start_ride.html')


# ──────────────────────────────────────────────────────────────
# SOS
# ──────────────────────────────────────────────────────────────

@login_required
def trigger_sos(request):
    if request.method != 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid request method'},
            status=400,
        )

    # Rate limiting: max 5 SOS calls per 60 seconds per user
    cache_key = f"sos_rate_limit_{request.user.id}"
    request_count = cache.get(cache_key, 0)
    if request_count >= 5:
        logger.warning("SOS rate limit exceeded for user=%s", request.user.username)
        return JsonResponse({
            'status': 'error',
            'message': 'Too many SOS requests. Please wait a minute before trying again.',
        }, status=429)

    cache.set(cache_key, request_count + 1, timeout=60)

    try:
        commuter = _get_or_create_commuter(request.user)

        active_ride = RideDetails.objects.filter(
            commuter=commuter, is_active=True,
        ).order_by('-start_time').first()

        if not active_ride:
            return JsonResponse({
                'status': 'error',
                'message': 'No active ride found. Please start a ride first.',
            })

        # Parse location from request body or form data
        location = 'Unknown'
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                location = data.get('location', 'Unknown')
            except json.JSONDecodeError:
                pass
        else:
            location = request.POST.get('location', 'Unknown')

        sos = SOSRequest.objects.create(ride=active_ride, location=location)

        logger.info(
            "SOS triggered: sos_id=%s ride_id=%s user=%s route=%s→%s",
            sos.id, active_ride.id, request.user.username,
            active_ride.source, active_ride.destination,
        )

        messages.success(request, 'SOS sent! Help is on the way.')
        return JsonResponse({
            'status': 'success',
            'sos_id': sos.id,
            'message': 'SOS triggered successfully',
            'ride_info': f"{active_ride.source} to {active_ride.destination}",
        })

    except Exception:
        logger.exception("Unexpected error in trigger_sos for user=%s", request.user.username)
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while processing your request.',
        }, status=500)


@login_required
def sos_status_latest(request):
    try:
        commuter = Commuter.objects.get(user=request.user)
        
        sos = SOSRequest.objects.filter(
            ride__commuter=commuter,
        ).select_related('ride').order_by('-timestamp').first()

        if not sos:
            return render(request, 'user/sos_status.html', {
                'error': 'No SOS requests found.',
            })

        if request.GET.get('ajax'):
            return JsonResponse({
                'status': sos.status,
                'ride_info': {
                    'vehicle_number': sos.ride.vehicle_number,
                    'source': sos.ride.source,
                    'destination': sos.ride.destination,
                    'timestamp': sos.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                },
            })

        return render(request, 'user/sos_status.html', {'sos': sos})
        
    except Commuter.DoesNotExist:
        return render(request, 'user/sos_status.html', {
            'error': 'Commuter profile not found.',
        })


@login_required 
def sos_status_by_id(request, sos_id):
    try:
        commuter = Commuter.objects.get(user=request.user)
        
        sos = SOSRequest.objects.select_related('ride').get(
            id=sos_id, ride__commuter=commuter,
        )
        
        if request.GET.get('ajax'):
            return JsonResponse({
                'status': sos.status,
                'ride_info': {
                    'vehicle_number': sos.ride.vehicle_number,
                    'source': sos.ride.source,
                    'destination': sos.ride.destination,
                    'timestamp': sos.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                },
            })
            
        return render(request, 'user/sos_status.html', {'sos': sos})
        
    except SOSRequest.DoesNotExist:
        return render(request, 'user/sos_status.html', {
            'error': 'SOS request not found or you do not have permission to view it.',
        })
    except Commuter.DoesNotExist:
        return render(request, 'user/sos_status.html', {
            'error': 'Commuter profile not found.',
        })


# ──────────────────────────────────────────────────────────────
# Location Tracking
# ──────────────────────────────────────────────────────────────

@login_required
def update_location(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'invalid request'}, status=405)

    try:
        data = json.loads(request.body)
        lat_raw = data.get('lat')
        lng_raw = data.get('lng')

        if lat_raw is None or lng_raw is None:
            return JsonResponse(
                {'status': 'error', 'message': 'lat and lng are required'},
                status=400,
            )

        try:
            lat, lng = validate_coordinates(lat_raw, lng_raw)
        except ValidationError as e:
            return JsonResponse(
                {'status': 'error', 'message': str(e.message)},
                status=400,
            )

        commuter = _get_or_create_commuter(request.user)
        active_ride = RideDetails.objects.filter(commuter=commuter, is_active=True).first()

        if not active_ride:
            return JsonResponse({'status': 'error', 'message': 'No active ride'})

        active_ride.current_lat = lat
        active_ride.current_lng = lng
        active_ride.save(update_fields=['current_lat', 'current_lng', 'last_updated'])
        return JsonResponse({'status': 'success'})

    except json.JSONDecodeError:
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid JSON'},
            status=400,
        )
    except Exception:
        logger.exception("Error in update_location for user=%s", request.user.username)
        return JsonResponse(
            {'status': 'error', 'message': 'Internal server error'},
            status=500,
        )


# ──────────────────────────────────────────────────────────────
# Incident Reporting
# ──────────────────────────────────────────────────────────────

@login_required
def report_incident(request):
    """Receive a JSON POST from the commuter dashboard to file an incident report."""
    if request.method != 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid request method.'},
            status=405,
        )

    try:
        commuter = Commuter.objects.get(user=request.user)
    except Commuter.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': 'Commuter profile not found.'},
            status=404,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid JSON.'},
            status=400,
        )

    incident_type = data.get('incident_type', 'Other')
    description = data.get('description', '')
    lat_raw = data.get('lat')
    lng_raw = data.get('lng')

    if lat_raw is None or lng_raw is None:
        return JsonResponse(
            {'status': 'error', 'message': 'Location (lat/lng) is required.'},
            status=400,
        )

    try:
        lat, lng = validate_coordinates(lat_raw, lng_raw)
    except ValidationError as e:
        return JsonResponse(
            {'status': 'error', 'message': str(e.message)},
            status=400,
        )

    active_ride = RideDetails.objects.filter(
        commuter=commuter, is_active=True,
    ).order_by('-start_time').first()

    IncidentReport.objects.create(
        commuter=commuter,
        ride=active_ride,
        incident_type=incident_type,
        description=description,
        lat=lat,
        lng=lng,
    )
    logger.info(
        "Incident reported: type=%s user=%s lat=%.4f lng=%.4f",
        incident_type, request.user.username, lat, lng,
    )
    return JsonResponse({'status': 'success', 'message': 'Incident reported successfully.'})


# ──────────────────────────────────────────────────────────────
# Home
# ──────────────────────────────────────────────────────────────

def home(request):
    return render(request, 'user/home.html')


# ──────────────────────────────────────────────────────────────
# End Ride (P2.2)
# ──────────────────────────────────────────────────────────────

@login_required
def end_ride(request):
    """End the currently active ride."""
    if request.method == 'POST':
        commuter = _get_or_create_commuter(request.user)
        active_ride = RideDetails.objects.filter(
            commuter=commuter, is_active=True,
        ).order_by('-start_time').first()

        if active_ride:
            active_ride.is_active = False
            active_ride.end_time = timezone.now()
            active_ride.save(update_fields=['is_active', 'end_time'])
            logger.info("Ride ended: id=%s user=%s", active_ride.id, request.user.username)
            messages.success(request, 'Ride ended safely. Stay safe!')
        else:
            messages.info(request, 'No active ride to end.')

    return redirect('user_dashboard')


# ──────────────────────────────────────────────────────────────
# Trip History (P2.3)
# ──────────────────────────────────────────────────────────────

@login_required
def trip_history(request):
    """Show past rides with incident and SOS counts."""
    commuter = _get_or_create_commuter(request.user)

    rides = (
        RideDetails.objects.filter(commuter=commuter)
        .annotate(
            incident_count=Count('incidentreport'),
            sos_count=Count('sos_requests'),
        )
        .order_by('-start_time')
    )

    return render(request, 'user/trip_history.html', {
        'rides': rides,
        'commuter': commuter,
    })


# ──────────────────────────────────────────────────────────────
# Trusted Contacts Management (P2.7)
# ──────────────────────────────────────────────────────────────

MAX_TRUSTED_CONTACTS = 3


@login_required
def manage_contacts(request):
    """Add or delete trusted emergency contacts."""
    commuter = _get_or_create_commuter(request.user)
    contacts = TrustedContact.objects.filter(commuter=commuter)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            if contacts.count() >= MAX_TRUSTED_CONTACTS:
                messages.warning(request, f'You can have at most {MAX_TRUSTED_CONTACTS} trusted contacts.')
            else:
                name = request.POST.get('contact_name', '').strip()
                phone = request.POST.get('contact_phone', '').strip()
                relationship = request.POST.get('contact_relationship', 'Other')

                if name and phone:
                    TrustedContact.objects.create(
                        commuter=commuter,
                        name=name,
                        phone=phone,
                        relationship=relationship,
                    )
                    logger.info("Trusted contact added: %s for user=%s", name, request.user.username)
                    messages.success(request, f'Contact "{name}" added.')
                else:
                    messages.error(request, 'Name and phone are required.')

        elif action == 'delete':
            contact_id = request.POST.get('contact_id')
            deleted, _ = TrustedContact.objects.filter(
                id=contact_id, commuter=commuter,
            ).delete()
            if deleted:
                messages.success(request, 'Contact removed.')
            else:
                messages.error(request, 'Contact not found.')

        return redirect('manage_contacts')

    return render(request, 'user/manage_contacts.html', {
        'contacts': contacts,
        'commuter': commuter,
        'can_add': contacts.count() < MAX_TRUSTED_CONTACTS,
    })
