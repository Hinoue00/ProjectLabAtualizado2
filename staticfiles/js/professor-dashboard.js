/* ===================================== */
/* 1. PROFESSOR-DASHBOARD.JS */
/* ===================================== */

/**
 * Professor Dashboard Main Controller
 * Gerencia as funcionalidades específicas do dashboard do professor
 */
class ProfessorDashboard {
    constructor() {
        this.isInitialized = false;
        this.stats = {
            pending: 0,
            approved: 0,
            total: 0
        };
        this.init();
    }

    init() {
        if (this.isInitialized) return;
        
        this.bindEvents();
        this.loadInitialData();
        this.setupNotifications();
        this.isInitialized = true;
        
        console.log('Professor Dashboard initialized');
    }

    bindEvents() {
        // Quick action buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.quick-action-btn') || e.target.closest('.quick-action-btn')) {
                this.handleQuickAction(e);
            }
            
            if (e.target.matches('.refresh-stats') || e.target.closest('.refresh-stats')) {
                this.refreshStats();
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.refreshStats();
            }
        });
    }

    loadInitialData() {
        this.refreshStats();
        this.loadUpcomingClasses();
        this.checkSchedulingAvailability();
    }

    async refreshStats() {
        try {
            const response = await fetch('/api/professor-stats/');
            const data = await response.json();
            
            this.stats = data;
            this.updateStatsDisplay(data);
            
        } catch (error) {
            console.error('Erro ao carregar estatísticas:', error);
            this.showNotification('Erro ao carregar dados', 'error');
        }
    }

    updateStatsDisplay(stats) {
        // Atualizar cards de estatísticas
        const statElements = {
            pending: document.querySelector('.stat-pending .stats-value'),
            approved: document.querySelector('.stat-approved .stats-value'),
            total: document.querySelector('.stat-total .stats-value'),
            thisWeek: document.querySelector('.stat-week .stats-value')
        };

        Object.entries(statElements).forEach(([key, element]) => {
            if (element && stats[key] !== undefined) {
                this.animateNumber(element, stats[key]);
            }
        });

        // Atualizar badges
        this.updateStatsBadges(stats);
    }

    animateNumber(element, newValue) {
        const current = parseInt(element.textContent) || 0;
        const duration = 500;
        const steps = 20;
        const increment = (newValue - current) / steps;
        let step = 0;

        const animation = setInterval(() => {
            step++;
            const value = Math.round(current + (increment * step));
            element.textContent = value;

            if (step >= steps) {
                element.textContent = newValue;
                clearInterval(animation);
            }
        }, duration / steps);
    }

    updateStatsBadges(stats) {
        // Atualizar badge de mudança percentual
        const changeBadge = document.querySelector('.percentage-change');
        if (changeBadge && stats.percentageChange !== undefined) {
            const change = stats.percentageChange;
            changeBadge.textContent = `${Math.abs(change)}% ${change >= 0 ? '↑' : '↓'}`;
            changeBadge.className = `badge rounded-pill ${change >= 0 ? 'bg-success' : 'bg-danger'}`;
        }
    }

    async loadUpcomingClasses() {
        try {
            const response = await fetch('/api/upcoming-classes/');
            const classes = await response.json();
            
            this.renderUpcomingClasses(classes);
            
        } catch (error) {
            console.error('Erro ao carregar próximas aulas:', error);
        }
    }

    renderUpcomingClasses(classes) {
        const container = document.querySelector('.upcoming-classes-list');
        if (!container) return;

        if (classes.length === 0) {
            container.innerHTML = `
                <div class="empty-state text-center py-4">
                    <i class="bi bi-calendar-x text-muted" style="font-size: 2rem;"></i>
                    <h5 class="mt-2 text-muted">Nenhuma aula agendada</h5>
                    <p class="text-muted">Você não tem aulas agendadas para os próximos dias.</p>
                </div>
            `;
            return;
        }

        const classesHTML = classes.map(classItem => `
            <div class="upcoming-class-item" data-class-id="${classItem.id}">
                <div class="class-time">
                    <i class="bi bi-clock"></i>
                    ${classItem.date} - ${classItem.time}
                </div>
                <div class="class-details">
                    <strong>${classItem.laboratory}</strong>
                    <span class="text-muted">${classItem.subject}</span>
                </div>
                <span class="badge bg-${classItem.status === 'approved' ? 'success' : 'warning'}">
                    ${classItem.statusDisplay}
                </span>
            </div>
        `).join('');

        container.innerHTML = classesHTML;
    }

    checkSchedulingAvailability() {
        const today = new Date();
        const dayOfWeek = today.getDay(); // 0 = domingo, 4 = quinta, 5 = sexta
        const isSchedulingDay = dayOfWeek === 4 || dayOfWeek === 5; // quinta ou sexta

        const scheduleBtn = document.querySelector('.btn-schedule');
        const warningMsg = document.querySelector('.scheduling-warning');

        if (scheduleBtn) {
            if (isSchedulingDay) {
                scheduleBtn.disabled = false;
                scheduleBtn.classList.remove('btn-secondary');
                scheduleBtn.classList.add('btn-primary');
            } else {
                scheduleBtn.disabled = true;
                scheduleBtn.classList.remove('btn-primary');
                scheduleBtn.classList.add('btn-secondary');
            }
        }

        if (warningMsg) {
            warningMsg.style.display = isSchedulingDay ? 'none' : 'block';
        }
    }

    handleQuickAction(e) {
        e.preventDefault();
        const action = e.target.closest('.quick-action-btn').dataset.action;

        switch (action) {
            case 'schedule':
                this.openScheduleModal();
                break;
            case 'calendar':
                window.location.href = '/calendar/';
                break;
            case 'requests':
                window.location.href = '/my-requests/';
                break;
            default:
                console.log('Ação não reconhecida:', action);
        }
    }

    openScheduleModal() {
        // Verificar se é dia de agendamento
        if (!this.isSchedulingDay()) {
            this.showNotification('Agendamentos só podem ser feitos às quintas e sextas-feiras', 'warning');
            return;
        }

        // Aqui integraria com o módulo de agendamento
        if (window.ScheduleModule) {
            window.ScheduleModule.openNewScheduleModal();
        } else {
            window.location.href = '/schedule/create/';
        }
    }

    isSchedulingDay() {
        const today = new Date();
        const dayOfWeek = today.getDay();
        return dayOfWeek === 4 || dayOfWeek === 5; // quinta ou sexta
    }

    setupNotifications() {
        // Verificar notificações a cada 30 segundos
        setInterval(() => {
            this.checkForNotifications();
        }, 30000);
    }

    async checkForNotifications() {
        try {
            const response = await fetch('/api/notifications/check/');
            const data = await response.json();

            if (data.hasNew) {
                this.showNotificationBadge(data.count);
                this.refreshStats(); // Atualizar stats se há notificações novas
            }
        } catch (error) {
            console.error('Erro ao verificar notificações:', error);
        }
    }

    showNotificationBadge(count) {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
            badge.classList.add('pulse-notification');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const container = document.querySelector('.notifications-container') || document.body;
        container.appendChild(notification);

        // Auto remove após 5 segundos
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

/* ===================================== */
/* 4. INITIALIZATION */
/* ===================================== */

// Inicializar módulos quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar apenas se estivermos na página do professor
    if (document.body.classList.contains('professor-dashboard') || 
        document.querySelector('.professor-dashboard')) {
        
        // Inicializar módulos
        window.ProfessorDashboard = new ProfessorDashboard();
        window.ScheduleModule = new ScheduleModule();
        window.AvailabilityChecker = new AvailabilityChecker();
        
        console.log('Todos os módulos do professor foram inicializados');
    }
});

// Export para uso em outros módulos
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ProfessorDashboard,
        ScheduleModule,
        AvailabilityChecker
    };
}
