# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from user.models import SOSRequest
from .models import Guardian
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout

def guardian_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                # Check if the user is a guardian
                guardian = Guardian.objects.get(user=user)
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

@login_required
def guardian_dashboard(request):
    try:
        guardian = Guardian.objects.get(user=request.user)
        # Show both Pending and Accepted requests
        pending_sos = SOSRequest.objects.filter(
            status__in=['Pending', 'Accepted'],
        ).order_by('-timestamp')  # Show newest first
        return render(request, 'admin_app/dashboard.html', {
            'sos_list': pending_sos,
            'guardian': guardian
        })
    except Guardian.DoesNotExist:
        messages.error(request, 'You are not registered as a guardian.')
        return redirect('register_guardian')

@login_required
def sos_details(request, sos_id):
    sos = get_object_or_404(SOSRequest, id=sos_id)
    return render(request, 'admin_app/sos_details.html', {'sos': sos})

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from user.models import SOSRequest
from .models import Guardian  # Adjust import based on your project

@login_required
@require_POST
def accept_sos(request, sos_id):
    try:
        sos = get_object_or_404(SOSRequest, id=sos_id)
        
        if sos.status == 'Pending':
            sos.status = 'Accepted'
            
            # Assign guardian if applicable
            try:
                guardian = Guardian.objects.get(user=request.user)
                sos.guardian = guardian
            except Guardian.DoesNotExist:
                pass
            
            sos.save()
            messages.success(request, f"SOS #{sos_id} has been accepted.")
        else:
            messages.info(request, f"SOS #{sos_id} has already been processed.")
        
        return redirect('guardian_dashboard')

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('guardian_dashboard')

@login_required  
@require_POST
def decline_sos(request, sos_id):
    try:
        sos = get_object_or_404(SOSRequest, id=sos_id)
        
        if sos.status == 'Pending':
            sos.status = 'Declined'
            sos.save()
            messages.warning(request, f"SOS #{sos_id} has been declined.")
        else:
            messages.info(request, f"SOS #{sos_id} has already been processed.")
        
        return redirect('guardian_dashboard')

    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('guardian_dashboard')

# Resolve SOS Request
@login_required
@require_POST
def resolve_sos(request, sos_id):
    try:
        guardian = Guardian.objects.get(user=request.user)
        sos = get_object_or_404(SOSRequest, id=sos_id)
        
        if sos.status == 'Accepted' and sos.guardian == guardian:
            sos.status = 'Resolved'
            sos.save()
            return JsonResponse({'success': True, 'message': 'SOS marked as resolved'})
        else:
            return JsonResponse({'error': 'Cannot resolve this request'}, status=400)
    except Guardian.DoesNotExist:
        return JsonResponse({'error': 'Guardian profile not found'}, status=403)
    except Exception as e:
        return JsonResponse({'error': f'Error resolving request: {str(e)}'}, status=500)

def register_guardian(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        organization = request.POST.get('organization')

        try:
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different username.')
                return render(request, 'admin_app/register_guardian.html')
            
            # Create new user
            user = User.objects.create_user(username=username, password=password)
            
            # Create guardian profile
            guardian = Guardian.objects.create(
                user=user,
                phone=phone,
                organization=organization,
            )
            
            messages.success(request, f'Guardian "{username}" registered successfully!')
            return redirect('register_guardian')
            
        except Exception as e:
            messages.error(request, f'Error registering guardian: {str(e)}')
            return render(request, 'admin_app/register_guardian.html')
    
    return render(request, 'admin_app/register_guardian.html')

def home(request):
    """Home page for users who aren't guardians"""
    return render(request, 'admin_app/home.html')

@login_required
def user_profile(request):
    """Show user their profile and role"""
    context = {
        'user': request.user,
        'is_guardian': Guardian.objects.filter(user=request.user).exists(),
        'is_admin': request.user.is_superuser,
    }
    return render(request, 'admin_app/profile.html', context)


def guardian_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            try:
                # Verify if user is a registered guardian
                guardian = Guardian.objects.get(user=user)
                login(request, user)
                return redirect('guardian_dashboard')
            except Guardian.DoesNotExist:
                messages.error(request, 'This account is not registered as a guardian.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_app/guardian_login.html')