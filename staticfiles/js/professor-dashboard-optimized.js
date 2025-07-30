/*
 * LabConnect - Professor Dashboard Optimized JS
 * Scripts específicos para o dashboard do professor
 */

// Configurações específicas do professor
window.professorConfig = {
    isSchedulingDay: {{ is_scheduling_day|yesno:"true,false" }},
    currentWeek: {
        start: '{{ week_start|date:"Y-m-d" }}',
        end: '{{ week_end|date:"Y-m-d" }}'
    },
    stats: {
        pending: {{ pending_count }},
        approved: {{ approved_count }},
        thisWeek: {{ this_week_count }},
        total: {{ total_schedules }}
    }
};

// 🔧 FUNÇÃO CORRIGIDA - loadWeekData
async function loadWeekData(weekOffset, department = null) {
    const calendarBody = document.getElementById('calendar-body');
    const weekOffsetInput = document.getElementById('week_offset_input');
    const departmentSelect = document.getElementById('department-select');
    
    if (!calendarBody) {
        console.error('❌ Calendar body não encontrado');
        return;
    }
    
    try {
        // 🔧 CORREÇÃO: Fix da sintaxe do departamento
        if (department === null) {
            department = departmentSelect ? departmentSelect.value : 'all';
        }
        
        console.log(`📅 Carregando dados: offset=${weekOffset}, department=${department}`);
        
        // Mostrar loading
        calendarBody.style.opacity = '0.6';
        calendarBody.style.pointerEvents = 'none';
        calendarBody.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <div class="mt-2">Carregando calendário...</div>
            </div>
        `;
        
        // 🔧 CORREÇÃO: URL correta para professor
        const url = `{% url 'professor_dashboard' %}?week_offset=${weekOffset}&department=${department}`;
        console.log(`📡 Fazendo requisição para: ${url}`);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log(`📡 Resposta recebida: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('📊 Dados recebidos:', data);
        
        if (data.success) {
            // 🔧 CORREÇÃO: Verificar se temos calendar_html
            if (data.calendar_html) {
                calendarBody.innerHTML = data.calendar_html;
            } else {
                // Se não tiver calendar_html, construir o calendário com os dados
                calendarBody.innerHTML = buildCalendarHTML(data.calendar_data);
            }
            
            // Atualizar controles
            if (weekOffsetInput) {
                weekOffsetInput.value = weekOffset;
            }
            
            if (departmentSelect) {
                departmentSelect.value = department;
            }
            
            // Atualizar URL
            const newUrl = new URL(window.location);
            newUrl.searchParams.set('week_offset', weekOffset);
            newUrl.searchParams.set('department', department);
            window.history.pushState({week_offset: weekOffset, department: department}, '', newUrl);
            
            console.log(`✅ Calendário do professor atualizado com sucesso`);
        } else {
            throw new Error(data.message || data.error || 'Erro desconhecido do servidor');
        }
        
    } catch (error) {
        console.error('💥 Erro ao carregar calendário:', error);
        calendarBody.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <strong>Erro ao carregar calendário:</strong> ${error.message}
                <br><small>Verifique o console para mais detalhes.</small>
            </div>
        `;
    } finally {
        // Restaurar interatividade
        calendarBody.style.opacity = '1';
        calendarBody.style.pointerEvents = 'auto';
    }
}

// 🔧 FUNÇÃO AUXILIAR: Construir HTML do calendário se necessário
function buildCalendarHTML(calendarData) {
    if (!calendarData || !Array.isArray(calendarData)) {
        return '<div class="alert alert-warning">Nenhum dado de calendário disponível</div>';
    }
    
    let html = '<div class="calendar-grid">';
    
    calendarData.forEach(day => {
        const isToday = new Date().toDateString() === new Date(day.date).toDateString();
        
        html += `
        <div class="calendar-day ${isToday ? 'today' : ''}">
            <div class="day-header">
                <div class="day-name">${new Date(day.date).toLocaleDateString('pt-BR', {weekday: 'short'})}</div>
                <div class="day-number">${new Date(day.date).toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'})}</div>
            </div>
            <div class="day-content">
        `;
        
        if (day.appointments && day.appointments.length > 0) {
            day.appointments.forEach(appointment => {
                html += `
                <div class="appointment-item status-${appointment.status}">
                    <div class="appointment-time">
                        <i class="bi bi-clock"></i>
                        ${appointment.start_time} - ${appointment.end_time}
                    </div>
                    <div class="appointment-lab">
                        <i class="bi bi-building"></i>
                        ${appointment.laboratory_name}
                    </div>
                    <div class="appointment-subject">
                        <i class="bi bi-book"></i>
                        ${appointment.subject || 'Sem disciplina'}
                    </div>
                    <div class="appointment-status badge bg-${appointment.status === 'approved' ? 'success' : appointment.status === 'pending' ? 'warning' : 'danger'}">
                        ${appointment.status_display || appointment.status}
                    </div>
                </div>
                `;
            });
        } else {
            html += '<div class="no-appointments"><i class="bi bi-calendar-x"></i> Sem agendamentos</div>';
        }
        
        html += '</div></div>';
    });
    
    html += '</div>';
    return html;
}

// 🔧 Event listeners para navegação do calendário
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Inicializando event listeners do calendário');
    
    const prevWeekLink = document.getElementById('prev-week-link');
    const nextWeekLink = document.getElementById('next-week-link');
    const todayLink = document.getElementById('today-link');
    const departmentSelect = document.getElementById('department-select');
    const weekOffsetInput = document.getElementById('week_offset_input');

    // Navegação semana anterior
    if (prevWeekLink) {
        prevWeekLink.addEventListener('click', function(e) {
            e.preventDefault();
            const currentOffset = weekOffsetInput ? parseInt(weekOffsetInput.value) : 0;
            console.log(`⬅️ Navegando para semana anterior: ${currentOffset - 1}`);
            loadWeekData(currentOffset - 1);
        });
    }

    // Navegação próxima semana
    if (nextWeekLink) {
        nextWeekLink.addEventListener('click', function(e) {
            e.preventDefault();
            const currentOffset = weekOffsetInput ? parseInt(weekOffsetInput.value) : 0;
            console.log(`➡️ Navegando para próxima semana: ${currentOffset + 1}`);
            loadWeekData(currentOffset + 1);
        });
    }

    // Voltar para hoje
    if (todayLink) {
        todayLink.addEventListener('click', function(e) {
            e.preventDefault();
            console.log(`🏠 Voltando para semana atual`);
            loadWeekData(0);
        });
    }

    // Filtro de departamento
    if (departmentSelect) {
        departmentSelect.addEventListener('change', function(e) {
            const currentOffset = weekOffsetInput ? parseInt(weekOffsetInput.value) : 0;
            const selectedDepartment = e.target.value;
            console.log(`🏢 Mudando departamento para: ${selectedDepartment}`);
            loadWeekData(currentOffset, selectedDepartment);
        });
    }
    
    console.log('✅ Event listeners configurados com sucesso');
});

// 🔧 Função para refresh do dashboard
function refreshDashboard() {
    console.log('🔄 Atualizando dashboard...');
    
    if (window.ProfessorDashboard) {
        window.ProfessorDashboard.refreshStats();
        window.ProfessorDashboard.loadUpcomingClasses();
    }
    
    if (window.AvailabilityChecker) {
        window.AvailabilityChecker.refreshAvailability();
    }
    
    // Recarregar calendário atual
    const weekOffsetInput = document.getElementById('week_offset_input');
    const departmentSelect = document.getElementById('department-select');
    const currentOffset = weekOffsetInput ? parseInt(weekOffsetInput.value) : 0;
    const currentDept = departmentSelect ? departmentSelect.value : 'all';
    
    loadWeekData(currentOffset, currentDept);
}

// Auto-refresh a cada 5 minutos
setInterval(refreshDashboard, 5 * 60 * 1000);

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+N para novo agendamento
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        if (window.professorConfig && window.professorConfig.isSchedulingDay) {
            const scheduleBtn = document.querySelector('.btn-schedule');
            if (scheduleBtn) scheduleBtn.click();
        }
    }
    
    // F5 para refresh completo da página
    if (e.key === 'F5') {
        e.preventDefault();
        window.location.reload();
    }
});

// 🔧 Inicialização adicional após carregamento
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔄 Inicializando dashboard do professor...');
    
    // Marcar body como professor dashboard
    document.body.classList.add('professor-dashboard');
    
    // Configurar tooltips se Bootstrap estiver disponível
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Inicializar módulos com tratamento de erro
    try {
        // Módulo principal do professor
        if (typeof ProfessorDashboard !== 'undefined') {
            window.ProfessorDashboard = new ProfessorDashboard();
            console.log('✅ ProfessorDashboard inicializado');
        }
        
        // Módulo de agendamento
        if (typeof ScheduleModule !== 'undefined') {
            window.ScheduleModule = new ScheduleModule();
            console.log('✅ ScheduleModule inicializado');
        }
        
        // Verificador de disponibilidade
        if (typeof AvailabilityChecker !== 'undefined') {
            window.AvailabilityChecker = new AvailabilityChecker();
            console.log('✅ AvailabilityChecker inicializado');
        } else {
            console.warn('⚠️ AvailabilityChecker não encontrado');
        }
        
        console.log('🚀 Todos os módulos do professor inicializados com sucesso!');
        
        // Verificar se as APIs estão funcionando
        setTimeout(() => {
            if (window.ProfessorDashboard) {
                window.ProfessorDashboard.refreshStats();
            }
        }, 2000);
        
    } catch (error) {
        console.error('❌ Erro ao inicializar módulos:', error);
        console.log('🔧 Sistema funcionará em modo básico');
    }
    
    console.log('✅ Professor Dashboard carregado com sucesso!');
});
