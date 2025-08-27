# reports/views.py
import csv
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Sum, Avg, F, Q
from django.template.loader import render_to_string
from accounts.views import is_technician
from .forms import ReportFilterForm
from .models import Report
from laboratories.models import Laboratory
from inventory.models import Material, MaterialCategory
from scheduling.models import ScheduleRequest
from accounts.models import User
# Importações condicionais para relatórios avançados
try:
    from weasyprint import HTML
except ImportError:
    HTML = None
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
import io
import base64
import tempfile
from datetime import datetime
from django.utils import timezone as django_timezone

def safe_datetime_for_excel(dt):
    """Convert timezone-aware datetime to naive for Excel compatibility."""
    if dt and hasattr(dt, 'tzinfo') and dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt

@login_required
@user_passes_test(is_technician)
def reports_dashboard(request):
    # ✅ OTIMIZAÇÃO: Cache de dados que mudam pouco
    cache_key = f"reports_dashboard_stats_{request.user.id}"
    cached_stats = cache.get(cache_key)
    
    if not cached_stats:
        # ✅ OTIMIZAÇÃO: Aggregations em uma query só
        today = timezone.now().date()
        this_month = today.replace(day=1)
        
        # Combined stats query
        combined_stats = {
            # Laboratory stats
            'total_labs': Laboratory.objects.count(),
            'active_labs': Laboratory.objects.filter(is_active=True).count(),
            
            # Material stats  
            'total_materials': Material.objects.count(),
            'materials_in_alert': Material.objects.filter(
                quantity__lt=F('minimum_stock')
            ).count(),
            
            # Materials near expiration (3 months)
            'materials_near_expiration': Material.objects.filter(
                expiration_date__isnull=False,
                expiration_date__lte=today + timezone.timedelta(days=90),
                expiration_date__gte=today
            ).count(),
            
            # Appointment stats for this month
            'appointments_this_month': ScheduleRequest.objects.filter(
                scheduled_date__gte=this_month,
                status='approved'
            ).count(),
            
            'pending_requests': ScheduleRequest.objects.filter(
                status='pending'
            ).count(),
        }
        
        # Cache por 15 minutos (dados não mudam constantemente)
        cache.set(cache_key, combined_stats, 60 * 15)
        cached_stats = combined_stats
    
    # ✅ OTIMIZAÇÃO: Recent reports com limit
    recent_reports = Report.objects.select_related(
        'created_by'
    ).filter(
        created_by=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'recent_reports': recent_reports,
        'form': ReportFilterForm(),
        **cached_stats
    }
    
    return render(request, 'reports/dashboard.html', context)

@login_required
@user_passes_test(is_technician)
def generate_report(request):
    if request.method == 'POST':
        form = ReportFilterForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            date_range_start = form.cleaned_data['date_range_start']
            date_range_end = form.cleaned_data['date_range_end']
            laboratory = form.cleaned_data.get('laboratory')
            include_charts = form.cleaned_data['include_charts']
            export_format = form.cleaned_data['export_format']
            
            # Save report record
            report = Report.objects.create(
                title=f"Relatório de {dict(Report.REPORT_TYPES).get(report_type)} - {datetime.now().strftime('%d/%m/%Y')}",
                report_type=report_type,
                created_by=request.user,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                filter_params={
                    'laboratory_id': laboratory.id if laboratory else None,
                    'include_charts': include_charts,
                }
            )
            
            # Redirect to appropriate report view
            if report_type == 'scheduling':
                return redirect('reports:scheduling_report', report_id=report.id, format=export_format)
            elif report_type == 'inventory':
                return redirect('reports:inventory_report', report_id=report.id, format=export_format)
            elif report_type == 'user_activity':
                return redirect('reports:user_activity_report', report_id=report.id, format=export_format)
    else:
        form = ReportFilterForm()
    
    return render(request, 'reports/generate.html', {'form': form})

@login_required
@user_passes_test(is_technician)
def scheduling_report(request, report_id, format='pdf'):
    report = Report.objects.get(id=report_id)
    
    # Get filter parameters
    date_start = report.date_range_start
    date_end = report.date_range_end
    laboratory_id = report.filter_params.get('laboratory_id')
    include_charts = report.filter_params.get('include_charts', True)
    
    # Build query
    query = ScheduleRequest.objects.filter(
        scheduled_date__range=[date_start, date_end]
    )
    
    if laboratory_id:
        query = query.filter(laboratory_id=laboratory_id)
    
    # Get data
    schedule_data = query.order_by('scheduled_date', 'start_time')
    
    # Prepare statistics - INCLUINDO DIFERENCIAÇÃO DE AGENDAMENTOS DE EXCEÇÃO
    total_requests = schedule_data.count()
    approved_requests = schedule_data.filter(status='approved').count()
    rejected_requests = schedule_data.filter(status='rejected').count()
    pending_requests = schedule_data.filter(status='pending').count()
    
    # Estatísticas de agendamentos de exceção
    exception_requests = schedule_data.filter(is_exception=True).count()
    normal_requests = schedule_data.filter(is_exception=False).count()
    
    # Separação por tipo de agendamento
    exception_data = schedule_data.filter(is_exception=True).order_by('scheduled_date', 'start_time')
    normal_data = schedule_data.filter(is_exception=False).order_by('scheduled_date', 'start_time')
    
    # Labs usage statistics - SEPARANDO NORMAL E EXCEÇÃO
    lab_usage = schedule_data.filter(status='approved').values('laboratory__name').annotate(
        count=Count('id'),
        exception_count=Count('id', filter=Q(is_exception=True)),
        normal_count=Count('id', filter=Q(is_exception=False))
    ).order_by('-count')
    
    # Professor statistics - SEPARANDO NORMAL E EXCEÇÃO
    professor_usage = schedule_data.filter(status='approved').values('professor__first_name', 'professor__last_name').annotate(
        count=Count('id'),
        exception_count=Count('id', filter=Q(is_exception=True)),
        normal_count=Count('id', filter=Q(is_exception=False))
    ).order_by('-count')
    
    # Data by weekday
    weekday_data = schedule_data.filter(status='approved').extra(
        select={'weekday': "EXTRACT(DOW FROM scheduled_date)"}
    ).values('weekday').annotate(count=Count('id')).order_by('weekday')
    
    weekday_mapping = {
        0: 'Segunda',
        1: 'Terça',
        2: 'Quarta',
        3: 'Quinta',
        4: 'Sexta',
        5: 'Sábado',
        6: 'Domingo'
    }
    
    weekday_data = [
        {'weekday': weekday_mapping.get(item['weekday']), 'count': item['count']}
        for item in weekday_data
    ]
    
    # Charts
    charts = []
    if include_charts and plt is not None:
        # Status distribution chart
        if total_requests > 0:
            plt.figure(figsize=(8, 4))
            labels = ['Aprovados', 'Rejeitados', 'Pendentes']
            sizes = [approved_requests, rejected_requests, pending_requests]
            colors = ['#28a745', '#dc3545', '#ffc107']
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Distribuição de Status dos Agendamentos')
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart1 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Distribuição de Status dos Agendamentos',
                'image': chart1
            })
        
        # Lab usage chart
        if lab_usage:
            plt.figure(figsize=(10, 6))
            labs = [item['laboratory__name'] for item in lab_usage]
            counts = [item['count'] for item in lab_usage]
            plt.bar(labs, counts, color='#4a6fa5')
            plt.xlabel('Laboratórios')
            plt.ylabel('Quantidade de Agendamentos')
            plt.title('Uso dos Laboratórios')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart2 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Uso dos Laboratórios',
                'image': chart2
            })
        
        # Weekday distribution chart
        if weekday_data:
            plt.figure(figsize=(10, 6))
            days = [item['weekday'] for item in weekday_data]
            counts = [item['count'] for item in weekday_data]
            plt.bar(days, counts, color='#17a2b8')
            plt.xlabel('Dia da Semana')
            plt.ylabel('Quantidade de Agendamentos')
            plt.title('Agendamentos por Dia da Semana')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart3 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Agendamentos por Dia da Semana',
                'image': chart3
            })
    
    context = {
        'report': report,
        'schedule_data': schedule_data,
        'total_requests': total_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'pending_requests': pending_requests,
        'lab_usage': lab_usage,
        'professor_usage': professor_usage,
        'weekday_data': weekday_data,
        'charts': charts,
        # NOVOS DADOS PARA AGENDAMENTOS DE EXCEÇÃO
        'exception_requests': exception_requests,
        'normal_requests': normal_requests,
        'exception_data': exception_data,
        'normal_data': normal_data,
    }
    
    if format == 'pdf':
        # Verificar se weasyprint está disponível
        if HTML is None:
            messages.error(request, 'Geração de PDF não disponível. Entre em contato com o administrador.')
            return redirect('reports:scheduling_report', report_id=report.id, format='html')
        
        # Render HTML
        html_string = render_to_string('reports/scheduling_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_file = html.write_pdf()
        
        # Create response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="scheduling_report_{report.id}.pdf"'
        return response
    
    elif format == 'excel':
        # Verificar se pandas está disponível
        if pd is None:
            messages.error(request, 'Exportação para Excel não disponível. Entre em contato com o administrador.')
            return redirect('reports:scheduling_report', report_id=report.id, format='html')
        
        # Create Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Schedule data
            df_schedule = pd.DataFrame([
                {
                    'ID': s.id,
                    'Data': s.scheduled_date,
                    'Horário': f"{s.start_time} - {s.end_time}",
                    'Laboratório': s.laboratory.name,
                    'Professor': s.professor.get_full_name(),
                    'Status': dict(ScheduleRequest.STATUS_CHOICES).get(s.status),
                    'Tipo': 'Agendamento de Exceção' if s.is_exception else 'Agendamento Normal',
                    'Motivo da Exceção': s.exception_reason if s.is_exception else 'N/A',
                    'Técnico Criador': s.created_by_technician.get_full_name() if s.is_exception and s.created_by_technician else 'N/A',
                    'Disciplina': s.subject or 'N/A',
                    'Descrição': s.description or 'N/A',
                }
                for s in schedule_data
            ])
            
            # Lab usage data
            df_lab_usage = pd.DataFrame(lab_usage)
            
            # Professor usage data
            df_professor_usage = pd.DataFrame([
                {
                    'Professor': f"{item['professor__first_name']} {item['professor__last_name']}",
                    'Quantidade': item['count']
                }
                for item in professor_usage
            ])
            
            # Weekday data
            df_weekday = pd.DataFrame(weekday_data)
            
            # Write to Excel
            df_schedule.to_excel(writer, sheet_name='Agendamentos', index=False)
            df_lab_usage.to_excel(writer, sheet_name='Uso por Laboratório', index=False)
            df_professor_usage.to_excel(writer, sheet_name='Uso por Professor', index=False)
            df_weekday.to_excel(writer, sheet_name='Uso por Dia da Semana', index=False)
        
        output.seek(0)
        
        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="scheduling_report_{report.id}.xlsx"'
        return response
    
    elif format == 'csv':
        # Create CSV file
        output = io.StringIO()
        
        # Write headers - INCLUINDO CAMPOS DE EXCEÇÃO
        writer = csv.writer(output)
        writer.writerow(['ID', 'Data', 'Horário', 'Laboratório', 'Professor', 'Status', 'Tipo', 'Motivo da Exceção', 'Técnico Criador', 'Disciplina', 'Descrição'])
        
        # Write data
        for s in schedule_data:
            writer.writerow([
                s.id,
                s.scheduled_date,
                f"{s.start_time} - {s.end_time}",
                s.laboratory.name,
                s.professor.get_full_name(),
                dict(ScheduleRequest.STATUS_CHOICES).get(s.status),
                'Agendamento de Exceção' if s.is_exception else 'Agendamento Normal',
                s.exception_reason if s.is_exception else 'N/A',
                s.created_by_technician.get_full_name() if s.is_exception and s.created_by_technician else 'N/A',
                s.subject or 'N/A',
                s.description or 'N/A'
            ])
        
        # Create response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="scheduling_report_{report.id}.csv"'
        return response
    
    return render(request, 'reports/scheduling.html', context)

@login_required
@user_passes_test(is_technician)
def inventory_report(request, report_id, format='pdf'):
    report = Report.objects.get(id=report_id)
    
    # Get filter parameters
    laboratory_id = report.filter_params.get('laboratory_id')
    include_charts = report.filter_params.get('include_charts', True)
    
    # Build query
    query = Material.objects.select_related('category', 'laboratory').all()
    
    if laboratory_id:
        query = query.filter(laboratory_id=laboratory_id)
    
    # Get data
    materials = query.order_by('laboratory__name', 'name')
    
    # Prepare statistics
    today = timezone.now().date()
    total_materials = materials.count()
    low_stock_materials = materials.filter(quantity__lt=F('minimum_stock')).count()
    
    # Materials near expiration (3 months)
    near_expiration_materials = materials.filter(
        expiration_date__isnull=False,
        expiration_date__lte=today + timezone.timedelta(days=90),
        expiration_date__gte=today
    ).count()
    
    # Expired materials
    expired_materials = materials.filter(
        expiration_date__isnull=False,
        expiration_date__lt=today
    ).count()
    
    # Category distribution
    category_distribution = materials.values('category__name', 'category__material_type').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-count')
    
    # Laboratory distribution
    lab_distribution = materials.values('laboratory__name').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-count')
    
    # Stock status
    stock_status = [
        {'status': 'Normal', 'count': total_materials - low_stock_materials},
        {'status': 'Baixo', 'count': low_stock_materials},
    ]
    
    # Expiration status  
    expiration_status = [
        {'status': 'Válidos', 'count': total_materials - near_expiration_materials - expired_materials},
        {'status': 'Próx. Vencimento', 'count': near_expiration_materials},
        {'status': 'Vencidos', 'count': expired_materials},
    ]
    
    # Charts
    charts = []
    if include_charts and plt is not None:
        # Category distribution chart
        if category_distribution:
            plt.figure(figsize=(10, 6))
            categories = [item['category__name'] for item in category_distribution]
            counts = [item['count'] for item in category_distribution]
            plt.bar(categories, counts, color='#4a6fa5')
            plt.xlabel('Categorias')
            plt.ylabel('Quantidade de Materiais')
            plt.title('Distribuição por Categoria')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart1 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Distribuição por Categoria',
                'image': chart1
            })
        
        # Laboratory distribution chart
        if lab_distribution:
            plt.figure(figsize=(10, 6))
            labs = [item['laboratory__name'] for item in lab_distribution]
            counts = [item['count'] for item in lab_distribution]
            plt.bar(labs, counts, color='#17a2b8')
            plt.xlabel('Laboratórios')
            plt.ylabel('Quantidade de Materiais')
            plt.title('Distribuição por Laboratório')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart2 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Distribuição por Laboratório',
                'image': chart2
            })
        
        # Stock status chart
        if total_materials > 0:
            plt.figure(figsize=(8, 4))
            labels = [item['status'] for item in stock_status]
            sizes = [item['count'] for item in stock_status]
            colors = ['#28a745', '#dc3545']
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Status de Estoque')
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart3 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Status de Estoque',
                'image': chart3
            })
    
    context = {
        'report': report,
        'materials': materials,
        'total_materials': total_materials,
        'low_stock_materials': low_stock_materials,
        'near_expiration_materials': near_expiration_materials,
        'expired_materials': expired_materials,
        'category_distribution': category_distribution,
        'lab_distribution': lab_distribution,
        'stock_status': stock_status,
        'expiration_status': expiration_status,
        'charts': charts,
    }
    
    if format == 'pdf':
        # Verificar se weasyprint está disponível
        if HTML is None:
            messages.error(request, 'Geração de PDF não disponível. Entre em contato com o administrador.')
            return redirect('reports:inventory_report', report_id=report.id, format='html')
        
        # Render HTML
        html_string = render_to_string('reports/inventory_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_file = html.write_pdf()
        
        # Create response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="inventory_report_{report.id}.pdf"'
        return response
    
    elif format == 'excel':
        # Verificar se pandas está disponível
        if pd is None:
            messages.error(request, 'Exportação para Excel não disponível. Entre em contato com o administrador.')
            return redirect('reports:inventory_report', report_id=report.id, format='html')
        
        # Create Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Materials data
            df_materials = pd.DataFrame([
                {
                    'ID': m.id,
                    'Nome': m.name,
                    'Categoria': m.category.name,
                    'Tipo': m.category.get_material_type_display(),
                    'Laboratório': m.laboratory.name,
                    'Quantidade': m.quantity,
                    'Estoque Mínimo': m.minimum_stock,
                    'Status': 'Baixo' if m.is_low_stock else 'Normal',
                    'Descrição': m.description,
                }
                for m in materials
            ])
            
            # Category distribution data
            df_category = pd.DataFrame([
                {
                    'Categoria': item['category__name'],
                    'Tipo': dict(MaterialCategory.CATEGORY_TYPES).get(item['category__material_type']),
                    'Quantidade de Materiais': item['count'],
                    'Quantidade Total': item['total_quantity']
                }
                for item in category_distribution
            ])
            
            # Laboratory distribution data
            df_lab = pd.DataFrame([
                {
                    'Laboratório': item['laboratory__name'],
                    'Quantidade de Materiais': item['count'],
                    'Quantidade Total': item['total_quantity']
                }
                for item in lab_distribution
            ])
            
            # Write to Excel
            df_materials.to_excel(writer, sheet_name='Materiais', index=False)
            df_category.to_excel(writer, sheet_name='Por Categoria', index=False)
            df_lab.to_excel(writer, sheet_name='Por Laboratório', index=False)
        
        output.seek(0)
        
        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="inventory_report_{report.id}.xlsx"'
        return response
    
    elif format == 'csv':
        # Create CSV file
        output = io.StringIO()
        
        # Write headers
        writer = csv.writer(output)
        writer.writerow(['ID', 'Nome', 'Categoria', 'Tipo', 'Laboratório', 'Quantidade', 'Estoque Mínimo', 'Status', 'Descrição'])
        
        # Write data
        for m in materials:
            writer.writerow([
                m.id,
                m.name,
                m.category.name,
                m.category.get_material_type_display(),
                m.laboratory.name,
                m.quantity,
                m.minimum_stock,
                'Baixo' if m.is_low_stock else 'Normal',
                m.description
            ])
        
        # Create response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="inventory_report_{report.id}.csv"'
        return response
    
    return render(request, 'reports/inventory.html', context)

@login_required
@user_passes_test(is_technician)
def user_activity_report(request, report_id, format='pdf'):
    report = Report.objects.get(id=report_id)
    
    # Get filter parameters
    date_start = report.date_range_start
    date_end = report.date_range_end
    include_charts = report.filter_params.get('include_charts', True)
    
    # Get users
    users = User.objects.filter(is_approved=True)
    
    # User type distribution
    user_type_distribution = users.values('user_type').annotate(
        count=Count('id')
    ).order_by('user_type')
    
    # User registration over time
    user_registrations = users.filter(
        registration_date__date__range=[date_start, date_end]
    ).extra({
        'month': "to_char(registration_date, 'YYYY-MM')"
    }).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Activity statistics
    professor_schedule_count = ScheduleRequest.objects.filter(
        request_date__date__range=[date_start, date_end]
    ).values('professor').annotate(
        count=Count('id')
    ).order_by('-count')
    
    technician_review_count = ScheduleRequest.objects.filter(
        review_date__date__range=[date_start, date_end]
    ).values('reviewed_by').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Combine professor data with user info
    professor_activity = []
    for item in professor_schedule_count:
        if item['professor']:
            try:
                user = User.objects.get(id=item['professor'])
                professor_activity.append({
                    'name': user.get_full_name(),
                    'count': item['count']
                })
            except User.DoesNotExist:
                pass
    
    # Combine technician data with user info
    technician_activity = []
    for item in technician_review_count:
        if item['reviewed_by']:
            try:
                user = User.objects.get(id=item['reviewed_by'])
                technician_activity.append({
                    'name': user.get_full_name(),
                    'count': item['count']
                })
            except User.DoesNotExist:
                pass
    
    # Charts
    charts = []
    if include_charts and plt is not None:
        # User type distribution chart
        if user_type_distribution:
            plt.figure(figsize=(8, 4))
            user_types = [dict(User.USER_TYPE_CHOICES).get(item['user_type']) for item in user_type_distribution]
            counts = [item['count'] for item in user_type_distribution]
            colors = ['#4a6fa5', '#17a2b8']
            plt.pie(counts, labels=user_types, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('Distribuição por Tipo de Usuário')
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart1 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Distribuição por Tipo de Usuário',
                'image': chart1
            })
        
        # User registration over time chart
        if user_registrations:
            plt.figure(figsize=(10, 6))
            months = [item['month'] for item in user_registrations]
            counts = [item['count'] for item in user_registrations]
            plt.bar(months, counts, color='#28a745')
            plt.xlabel('Mês')
            plt.ylabel('Número de Registros')
            plt.title('Registros de Usuários ao Longo do Tempo')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart2 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Registros de Usuários ao Longo do Tempo',
                'image': chart2
            })
        
        # Professor activity chart
        if professor_activity:
            plt.figure(figsize=(10, 6))
            names = [item['name'] for item in professor_activity[:10]]  # Top 10
            counts = [item['count'] for item in professor_activity[:10]]
            plt.bar(names, counts, color='#dc3545')
            plt.xlabel('Professor')
            plt.ylabel('Número de Agendamentos')
            plt.title('Atividade dos Professores (Top 10)')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            chart3 = base64.b64encode(image_png).decode('utf-8')
            charts.append({
                'title': 'Atividade dos Professores (Top 10)',
                'image': chart3
            })
    
    context = {
        'report': report,
        'users': users,
        'user_type_distribution': user_type_distribution,
        'user_registrations': user_registrations,
        'professor_activity': professor_activity,
        'technician_activity': technician_activity,
        'charts': charts,
    }
    
    if format == 'pdf':
        # Verificar se weasyprint está disponível
        if HTML is None:
            messages.error(request, 'Geração de PDF não disponível. Entre em contato com o administrador.')
            return redirect('reports:user_activity_report', report_id=report.id, format='html')
        
        # Render HTML
        html_string = render_to_string('reports/user_activity_pdf.html', context)
        
        # Generate PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf_file = html.write_pdf()
        
        # Create response
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="user_activity_report_{report.id}.pdf"'
        return response
    
    elif format == 'excel':
        # Verificar se pandas está disponível
        if pd is None:
            messages.error(request, 'Exportação para Excel não disponível. Entre em contato com o administrador.')
            return redirect('reports:user_activity_report', report_id=report.id, format='html')
        
        # Create Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Users data
            df_users = pd.DataFrame([
                {
                    'ID': u.id,
                    'Nome': u.get_full_name(),
                    'E-mail': u.email,
                    'Tipo': dict(User.USER_TYPE_CHOICES).get(u.user_type),
                    'Telefone': u.phone_number,
                    'Data de Registro': safe_datetime_for_excel(u.registration_date),  # Convert timezone-aware to naive for Excel
                }
                for u in users
            ])
            
            # Professor activity data
            df_professor = pd.DataFrame(professor_activity)
            
            # Technician activity data
            df_technician = pd.DataFrame(technician_activity)
            
            # Write to Excel
            df_users.to_excel(writer, sheet_name='Usuários', index=False)
            df_professor.to_excel(writer, sheet_name='Atividade de Professores', index=False)
            df_technician.to_excel(writer, sheet_name='Atividade de Laboratoristas', index=False)
        
        output.seek(0)
        
        # Create response
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="user_activity_report_{report.id}.xlsx"'
        return response
    
    elif format == 'csv':
        # Create CSV file
        output = io.StringIO()
        
        # Write headers
        writer = csv.writer(output)
        writer.writerow(['ID', 'Nome', 'E-mail', 'Tipo', 'Telefone', 'Data de Registro'])
        
        # Write data
        for u in users:
            writer.writerow([
                u.id,
                u.get_full_name(),
                u.email,
                dict(User.USER_TYPE_CHOICES).get(u.user_type),
                u.phone_number,
                u.registration_date,
            ])
        
        # Create response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="user_activity_report_{report.id}.csv"'
        return response
    
    return render(request, 'reports/user_activity.html', context)