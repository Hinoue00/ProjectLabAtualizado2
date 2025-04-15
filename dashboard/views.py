from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.views import is_technician, is_professor
from django.utils import timezone
from datetime import timedelta
from scheduling.models import DraftScheduleRequest, ScheduleRequest
from inventory.models import Material
from accounts.models import User
from django.db import models
from django.db.models import Count, F

@login_required
@user_passes_test(is_technician)
def technician_dashboard(request):
    # Get current week dates
    today = timezone.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Previous week dates
    prev_week_start = start_of_week - timedelta(days=7)
    prev_week_end = end_of_week - timedelta(days=7)
    
    # Weekly appointments
    current_week_appointments = ScheduleRequest.objects.filter(
        scheduled_date__range=[start_of_week, end_of_week],
        status='approved'
    )
    
    previous_week_appointments = ScheduleRequest.objects.filter(
        scheduled_date__range=[prev_week_start, prev_week_end],
        status='approved'
    )
    
    # Calculate percentage change
    current_count = current_week_appointments.count()
    previous_count = previous_week_appointments.count()
    
    if previous_count > 0:
        percentage_change = ((current_count - previous_count) / previous_count) * 100
    else:
        percentage_change = 100 if current_count > 0 else 0
    
    # Pending requests
    pending_approvals = User.objects.filter(is_approved=False).count()
    pending_appointment_objects = ScheduleRequest.objects.filter(status='pending').order_by('scheduled_date')[:5]
    
    # Materials in alert (low stock)
    materials_in_alert = Material.objects.filter(quantity__lte=models.F('minimum_stock'))
    
    # Active professors with approved schedules
    active_professors = User.objects.filter(
        user_type='professor',
        schedulerequest__status='approved',
        schedulerequest__scheduled_date__gte=today
    ).distinct()
    
    # Calendar data - appointments for each day this week
    calendar_data = []
    for i in range(5):  # Apenas 5 dias (segunda a sexta)
        day = start_of_week + timedelta(days=i)
        day_appointments = current_week_appointments.filter(scheduled_date=day)
        calendar_data.append({
            'date': day,
            'appointments': day_appointments
        })
    
    # Recent appointment history
    recent_appointments = ScheduleRequest.objects.filter(
        status__in=['approved', 'rejected']
    ).order_by('-review_date')[:10]
    
    context = {
        'current_week_appointments': current_week_appointments,
        'current_count': current_count,
        'percentage_change': percentage_change,
        'pending_approvals': pending_approvals,
        'pending_appointments': pending_appointment_objects,
        'materials_in_alert': materials_in_alert,
        'active_professors': active_professors,
        'calendar_data': calendar_data,
        'recent_appointments': recent_appointments,
    }
    
    return render(request, 'technician.html', context)

@login_required
@user_passes_test(is_professor)
def professor_dashboard(request):
    # Get current user
    professor = request.user
    
    # Today's date
    today = timezone.now().date()
    
    # Upcoming approved lab reservations
    upcoming_reservations = ScheduleRequest.objects.filter(
        professor=professor,
        status='approved',
        scheduled_date__gte=today
    ).order_by('scheduled_date')
    
    # Pending requests
    pending_requests = ScheduleRequest.objects.filter(
        professor=professor,
        status='pending'
    ).order_by('scheduled_date')
    
    # Past reservations
    past_reservations = ScheduleRequest.objects.filter(
        professor=professor,
        scheduled_date__lt=today
    ).order_by('-scheduled_date')[:10]
    
    # Check if today is Thursday or Friday (for showing scheduling button)
    is_scheduling_day = today.weekday() in [3, 4]  # 3=Thursday, 4=Friday
    
    # Calendar days for the current week
    start_of_week = today - timedelta(days=today.weekday())
    calendar_days = []
    
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        # Check if there are events on this day
        has_events = ScheduleRequest.objects.filter(
            professor=professor,
            scheduled_date=day,
            status='approved'
        ).exists()
        
        calendar_days.append({
            'date': day,
            'is_today': day == today,
            'has_events': has_events
        })
    
    # Today's events
    today_events = ScheduleRequest.objects.filter(
        professor=professor,
        scheduled_date=today,
        status='approved'
    ).order_by('start_time')

    # Add draft requests
    draft_requests = DraftScheduleRequest.objects.filter(
        professor=request.user
    ).order_by('scheduled_date')
    
    context = {
        'upcoming_reservations': upcoming_reservations,
        'pending_requests': pending_requests,
        'past_reservations': past_reservations,
        'is_scheduling_day': is_scheduling_day,
        'calendar_days': calendar_days,
        'today_events': today_events,
        'today': today,
        'draft_requests': draft_requests,
    }
    
    return render(request, 'professor.html', context)