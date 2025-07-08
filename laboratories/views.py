# laboratories/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from accounts.views import is_technician
from laboratories.models import Laboratory
from .forms import LaboratoryForm
from inventory.models import Material
from scheduling.models import ScheduleRequest
from django.utils import timezone
from datetime import timedelta

@login_required
def laboratory_list(request):
    laboratories = Laboratory.objects.all()
    
    # For professors, add availability info
    if request.user.user_type == 'professor':
        today = timezone.now().date()
        next_week_start = today + timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timedelta(days=4)  # Monday to Friday
        
        # Check if today is a scheduling day (Thursday or Friday)
        is_scheduling_day = today.weekday() in [3, 4]
        
        # Get approved schedules for next week
        next_week_schedules = ScheduleRequest.objects.filter(
            scheduled_date__range=[next_week_start, next_week_end],
            status='approved'
        )
        
        # Create a dict with lab availability
        lab_availability = {}
        
        for lab in laboratories:
            # Get schedules for this lab
            lab_schedules = next_week_schedules.filter(laboratory=lab)
            
            # Create a dict for each day
            daily_availability = {}
            
            for i in range(5):  # Monday to Friday
                day = next_week_start + timedelta(days=i)
                day_name = day.strftime('%A')
                
                # Get schedules for this day
                day_schedules = lab_schedules.filter(scheduled_date=day)
                
                if day_schedules.exists():
                    # Lab has some bookings this day
                    time_slots = []
                    for schedule in day_schedules:
                        time_slots.append({
                            'start': schedule.start_time,
                            'end': schedule.end_time,
                            'professor': schedule.professor.get_full_name()
                        })
                    
                    daily_availability[day_name] = {
                        'date': day,
                        'available': True,  # Some time slots might still be available
                        'time_slots': time_slots
                    }
                else:
                    # Lab is fully available this day
                    daily_availability[day_name] = {
                        'date': day,
                        'available': True,
                        'time_slots': []
                    }
            
            lab_availability[lab.id] = daily_availability
        
        context = {
            'laboratories': laboratories,
            'lab_availability': lab_availability,
            'is_scheduling_day': is_scheduling_day,
            'next_week_start': next_week_start,
            'next_week_end': next_week_end
        }
    else:
        # For technicians, just show the list
        context = {
            'laboratories': laboratories,
            'lab_availability': {}
        }
    
    return render(request, 'list.html', context)

@login_required
def laboratory_detail(request, pk):
    laboratory = get_object_or_404(Laboratory, pk=pk)
    
    # Get materials in this laboratory
    materials = Material.objects.filter(laboratory=laboratory)
    
    # Get upcoming schedules
    today = timezone.now().date()
    upcoming_schedules = ScheduleRequest.objects.filter(
        laboratory_id=pk,
        scheduled_date__gte=today,
        status='approved'
    ).order_by('scheduled_date', 'start_time')
    
    context = {
        'laboratory': laboratory,
        'materials': materials,
        'upcoming_schedules': upcoming_schedules
    }
    
    return render(request, 'detail.html', context)

@login_required
@user_passes_test(is_technician)
def laboratory_create(request):
    if request.method == 'POST':
        form = LaboratoryForm(request.POST)
        if form.is_valid():
            laboratory = form.save()
            messages.success(
                request, 
                f'Laboratório "{laboratory.name}" criado com sucesso! '
                f'Departamentos: {laboratory.get_departments_display()}'
            )
            return redirect('laboratory_list')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = LaboratoryForm()
    
    return render(request, 'form.html', {
        'form': form,
        'title': 'Adicionar Laboratório',
        'submit_text': 'Criar Laboratório'
    })

@login_required
@user_passes_test(is_technician)
def laboratory_update(request, pk):
    laboratory = get_object_or_404(Laboratory, pk=pk)
    
    if request.method == 'POST':
        form = LaboratoryForm(request.POST, instance=laboratory)
        if form.is_valid():
            laboratory = form.save()
            messages.success(
                request, 
                f'Laboratório "{laboratory.name}" atualizado com sucesso! '
                f'Departamentos: {laboratory.get_departments_display()}'
            )
            return redirect('laboratory_list')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = LaboratoryForm(instance=laboratory)
    
    return render(request, 'form.html', {
        'form': form,
        'title': f'Editar {laboratory.name}',
        'submit_text': 'Salvar Alterações',
        'laboratory': laboratory
    })

@login_required
@user_passes_test(is_technician)
def laboratory_delete(request, pk):
    laboratory = get_object_or_404(Laboratory, pk=pk)
    
    if request.method == 'POST':
        laboratory.delete()
        messages.success(request, 'Laboratório excluído com sucesso.')
        return redirect('laboratory_list')
    
    return render(request, 'confirm_delete.html', {
        'laboratory': laboratory
    })