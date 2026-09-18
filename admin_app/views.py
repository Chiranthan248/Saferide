import logging
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from django.utils import timezone

from user.models import SOSRequest, RideDetails, IncidentReport
from .models import Guardian

logger = logging.getLogger(__name__)


def guardian_required(view_func):
    """Allow sensitive guardian actions only to an authenticated Guardian."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not Guardian.objects.filter(user=request.user).exists():
            messages.error(request, 'A guardian account is required to access this page.')
            return redirect('guardian_login')
        return view_func(request, *args, **kwargs)
    return wrapped


# ──────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────

def guardian_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                Guardian.objects.get(user=user)
                login(request, user)
                return redirect('guardian_dashboard')
            except Guardian.DoesNotExist:
                messages.error(request, 'This account is not registered as a guardian.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_app/guardian_login.html')


@login_required
def guardian_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('guardian_login')


# ──────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────

@guardian_required
def guardian_dashboard(request):
    try:
        guardian = Guardian.objects.get(user=request.user)
        # P1.12: select_related to eliminate N+1 queries
        pending_sos = SOSRequest.objects.filter(
            status__in=['Pending', 'Accepted'],
        ).select_related(
            'ride__commuter__user',
            'guardian__user',
        ).order_by('-timestamp')

        # Real-time stats for dashboard cards
        today = timezone.now().date()
        active_ride_count = RideDetails.objects.filter(is_active=True).count()
        incidents_today = IncidentReport.objects.filter(
            timestamp__date=today,
        ).count()
        resolved_today = SOSRequest.objects.filter(
            status='Resolved',
            timestamp__date=today,
        ).count()

        return render(request, 'admin_app/dashboard.html', {
            'sos_list': pending_sos,
            'guardian': guardian,
            'active_ride_count': active_ride_count,
            'incidents_today': incidents_today,
            'resolved_today': resolved_today,
        })
    except Guardian.DoesNotExist:
        messages.error(request, 'You are not registered as a guardian.')
        return redirect('register_guardian')


# ──────────────────────────────────────────────────────────────
# SOS Management
# ──────────────────────────────────────────────────────────────

@guardian_required
def sos_details(request, sos_id):
    sos = get_object_or_404(
        SOSRequest.objects.select_related('ride__commuter__user', 'guardian__user'),
        id=sos_id,
    )
    return render(request, 'admin_app/sos_details.html', {'sos': sos})


@guardian_required
@require_POST
def accept_sos(request, sos_id):
    try:
        sos = get_object_or_404(SOSRequest, id=sos_id)
        
        if sos.status == 'Pending':
            sos.status = 'Accepted'
            try:
                guardian = Guardian.objects.get(user=request.user)
                sos.guardian = guardian
            except Guardian.DoesNotExist:
                pass
            
            sos.save()
            logger.info("SOS #%s accepted by %s", sos_id, request.user.username)
            messages.success(request, f"SOS #{sos_id} has been accepted.")
        else:
            messages.info(request, f"SOS #{sos_id} has already been processed.")
        
        return redirect('guardian_dashboard')

    except Exception:
        logger.exception("Error accepting SOS #%s", sos_id)
        messages.error(request, "An error occurred while processing the request.")
        return redirect('guardian_dashboard')


@guardian_required
@require_POST
def decline_sos(request, sos_id):
    try:
        sos = get_object_or_404(SOSRequest, id=sos_id)
        
        if sos.status == 'Pending':
            sos.status = 'Declined'
            sos.save()
            logger.info("SOS #%s declined by %s", sos_id, request.user.username)
            messages.warning(request, f"SOS #{sos_id} has been declined.")
        else:
            messages.info(request, f"SOS #{sos_id} has already been processed.")
        
        return redirect('guardian_dashboard')

    except Exception:
        logger.exception("Error declining SOS #%s", sos_id)
        messages.error(request, "An error occurred while processing the request.")
        return redirect('guardian_dashboard')


@guardian_required
@require_POST
def resolve_sos(request, sos_id):
    try:
        guardian = Guardian.objects.get(user=request.user)
        sos = get_object_or_404(SOSRequest, id=sos_id)
        
        if sos.status == 'Accepted' and sos.guardian == guardian:
            sos.status = 'Resolved'
            sos.save()
            logger.info("SOS #%s resolved by %s", sos_id, request.user.username)
            return JsonResponse({'success': True, 'message': 'SOS marked as resolved'})
        else:
            return JsonResponse({'error': 'Cannot resolve this request'}, status=400)
    except Guardian.DoesNotExist:
        return JsonResponse({'error': 'Guardian profile not found'}, status=403)
    except Exception:
        logger.exception("Error resolving SOS #%s", sos_id)
        return JsonResponse({'error': 'An error occurred.'}, status=500)


# ──────────────────────────────────────────────────────────────
# Guardian Registration (superuser-only)
# ──────────────────────────────────────────────────────────────

@login_required
def register_guardian(request):
    # P1.3: Only superusers can register new guardians
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can register guardians.')
        return redirect('guardian_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        organization = request.POST.get('organization', '')

        try:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different username.')
                return render(request, 'admin_app/register_guardian.html')
            
            user = User.objects.create_user(username=username, password=password)
            
            Guardian.objects.create(
                user=user,
                phone=phone,
                organization=organization,
            )
            
            logger.info("Guardian '%s' registered by admin %s", username, request.user.username)
            messages.success(request, f'Guardian "{username}" registered successfully!')
            return redirect('register_guardian')
            
        except Exception:
            logger.exception("Error registering guardian '%s'", username)
            messages.error(request, 'Error registering guardian. Please try again.')
            return render(request, 'admin_app/register_guardian.html')
    
    return render(request, 'admin_app/register_guardian.html')


# ──────────────────────────────────────────────────────────────
# Misc Pages
# ──────────────────────────────────────────────────────────────

def home(request):
    """Home page for users who aren't guardians."""
    return render(request, 'admin_app/home.html')


@login_required
def user_profile(request):
    """Show user their profile and role."""
    context = {
        'user': request.user,
        'is_guardian': Guardian.objects.filter(user=request.user).exists(),
        'is_admin': request.user.is_superuser,
    }
    return render(request, 'admin_app/profile.html', context)
