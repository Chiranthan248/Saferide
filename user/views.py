from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User  # Add this import
from .models import Commuter, RideDetails, SOSRequest
from django.contrib import messages
from django.http import JsonResponse
import json

# User Login
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

# User Registration
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        phone = request.POST['phone']
        emergency_contact = request.POST['emergency_contact']
        address = request.POST['address']

        if User.objects.filter(username=username).exists():
            return render(request, 'user/register.html', {'error': 'Username already exists'})

        user = User.objects.create_user(username=username, password=password)
        user.email = email
        user.save()

        Commuter.objects.create(user=user, phone=phone, emergency_contact=emergency_contact, address=address)
        return redirect('login')

    return render(request, 'user/register.html')


# User Dashboard (Active Rides)
@login_required
def user_dashboard(request):
    try:
        # Check if a Commuter profile exists for this user
        commuter = Commuter.objects.get(user=request.user)
    except Commuter.DoesNotExist:
        # Auto-create the commuter profile for superusers or users without one to make the app foolproof
        commuter = Commuter.objects.create(
            user=request.user, 
            phone="0000000000", 
            emergency_contact="0000000000", 
            address="Not specified"
        )
        
    active_ride = RideDetails.objects.filter(commuter=commuter, is_active=True).first()
    return render(request, 'user/dashboard.html', {'active_ride': active_ride})

# Start a New Ride
# Replace your existing start_ride function with this:

@login_required
def start_ride(request):
    try:
        commuter = Commuter.objects.get(user=request.user)
    except Commuter.DoesNotExist:
        commuter = Commuter.objects.create(
            user=request.user, phone="0000000000", emergency_contact="0000000000", address="Not specified"
        )
        
    if request.method == 'POST':
        # Deactivate all previous rides for this commuter
        RideDetails.objects.filter(commuter=commuter, is_active=True).update(is_active=False)
        
        vehicle_number = request.POST.get('vehicle_number', 'Unknown')
        vehicle_type = request.POST.get('vehicle_type', 'Unknown')
        source = request.POST.get('source', '')
        destination = request.POST.get('destination', '')

        # Create new active ride
        new_ride = RideDetails.objects.create(
            commuter=commuter,
            vehicle_number=vehicle_number,
            vehicle_type=vehicle_type,
            source=source,
            destination=destination,
            is_active=True  # Explicitly set as active
        )
        
        print(f"Started new ride {new_ride.id}: {source} to {destination}")  # Debug
        
        return redirect('user_dashboard')
        
    return render(request, 'user/start_ride.html')

# Trigger SOS
# Replace your existing trigger_sos function with this improved version:

# Replace your existing SOS status views with these improved versions:

@login_required
def sos_status_latest(request):
    try:
        commuter = Commuter.objects.get(user=request.user)
        
        # Get the latest SOS request for this commuter
        # This will get SOS requests ordered by timestamp (newest first)
        sos = SOSRequest.objects.filter(
            ride__commuter=commuter
        ).select_related('ride').order_by('-timestamp').first()

        if not sos:
            return render(request, 'user/sos_status.html', {
                'error': 'No SOS requests found.'
            })

        if request.GET.get('ajax'):
            return JsonResponse({
                'status': sos.status,
                'ride_info': {
                    'vehicle_number': sos.ride.vehicle_number,
                    'source': sos.ride.source,
                    'destination': sos.ride.destination,
                    'timestamp': sos.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
            })

        return render(request, 'user/sos_status.html', {'sos': sos})
        
    except Commuter.DoesNotExist:
        return render(request, 'user/sos_status.html', {
            'error': 'Commuter profile not found.'
        })

@login_required 
def sos_status_by_id(request, sos_id):
    try:
        commuter = Commuter.objects.get(user=request.user)
        
        # Make sure the SOS belongs to this commuter
        sos = SOSRequest.objects.select_related('ride').get(
            id=sos_id, 
            ride__commuter=commuter
        )
        
        if request.GET.get('ajax'):
            return JsonResponse({
                'status': sos.status,
                'ride_info': {
                    'vehicle_number': sos.ride.vehicle_number,
                    'source': sos.ride.source,
                    'destination': sos.ride.destination,
                    'timestamp': sos.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
            })
            
        return render(request, 'user/sos_status.html', {'sos': sos})
        
    except SOSRequest.DoesNotExist:
        return render(request, 'user/sos_status.html', {
            'error': 'SOS request not found or you do not have permission to view it.'
        })
    except Commuter.DoesNotExist:
        return render(request, 'user/sos_status.html', {
            'error': 'Commuter profile not found.'
        })

@login_required
def update_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat = data.get('lat')
            lng = data.get('lng')

            if lat and lng:
                try:
                    commuter = Commuter.objects.get(user=request.user)
                except Commuter.DoesNotExist:
                    commuter = Commuter.objects.create(
                        user=request.user, phone="0000000000", emergency_contact="0000000000", address="Not specified"
                    )
                
                active_ride = RideDetails.objects.filter(commuter=commuter, is_active=True).first()
                if active_ride:
                    active_ride.current_lat = float(lat)
                    active_ride.current_lng = float(lng)
                    active_ride.save()
                    return JsonResponse({'status': 'success'})
                return JsonResponse({'status': 'error', 'message': 'No active ride'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid request'})

# Also, let's improve the trigger_sos view to ensure it uses the correct active ride
@login_required
def trigger_sos(request):
    if request.method == 'POST':
        try:
            try:
                commuter = Commuter.objects.get(user=request.user)
            except Commuter.DoesNotExist:
                commuter = Commuter.objects.create(
                    user=request.user, phone="0000000000", emergency_contact="0000000000", address="Not specified"
                )
            
            # Get the most recent active ride for this commuter
            active_ride = RideDetails.objects.filter(
                commuter=commuter, 
                is_active=True
            ).order_by('-start_time').first()
            
            if active_ride:
                # Get location from POST data
                location = 'Unknown'
                if request.content_type == 'application/json':
                    try:
                        data = json.loads(request.body)
                        location = data.get('location', 'Unknown')
                    except json.JSONDecodeError:
                        pass
                else:
                    location = request.POST.get('location', 'Unknown')
                
                # Create SOS request
                sos = SOSRequest.objects.create(
                    ride=active_ride,
                    location=location,
                )
                
                # Debug: Print information to help troubleshoot
                print(f"Created SOS {sos.id} for ride {active_ride.id} ({active_ride.source} to {active_ride.destination})")
                
                messages.success(request, 'SOS sent! Help is on the way.')
                return JsonResponse({
                    'status': 'success', 
                    'sos_id': sos.id,
                    'message': 'SOS triggered successfully',
                    'ride_info': f"{active_ride.source} to {active_ride.destination}"
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'No active ride found. Please start a ride first.'
                })
                
        except Commuter.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'Commuter profile not found.'
            })
        except Exception as e:
            print(f"Error in trigger_sos: {e}")  # Debug print
            return JsonResponse({
                'status': 'error', 
                'message': 'An error occurred while processing your request.'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    }, status=400)


def home(request):
    return render(request, 'user/home.html')
