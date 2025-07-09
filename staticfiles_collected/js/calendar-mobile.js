// dashboard/static/js/calendar-mobile.js

// Utilitários mobile
const MobileUtils = {
    // Detectar dispositivo mobile
    isMobile: () => {
        return window.innerWidth < 768 || 
               ('ontouchstart' in window) || 
               (navigator.maxTouchPoints > 0);
    },
    
    // Detectar orientação
    isLandscape: () => {
        return window.innerWidth > window.innerHeight;
    },
    
    // Vibração háptica (se suportado)
    vibrate: (duration = 10) => {
        if ('vibrate' in navigator) {
            navigator.vibrate(duration);
        }
    },
    
    // Prevenir zoom em inputs
    preventZoom: () => {
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        });
        
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = new Date().getTime();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }
};

// Calendário Mobile Interativo
class MobileCalendar {
    constructor(container) {
        this.container = container;
        this.currentMonth = new Date();
        this.selectedDate = null;
        this.events = [];
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.isSwipping = false;
        
        this.init();
    }
    
    init() {
        this.setupSwipeGestures();
        this.setupTouchFeedback();
        this.setupPullToRefresh();
        this.render();
    }
    
    setupSwipeGestures() {
        let touchStartX = 0;
        let touchStartY = 0;
        let touchEndX = 0;
        let touchEndY = 0;
        
        this.container.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });
        
        this.container.addEventListener('touchmove', (e) => {
            if (!this.isSwipping) {
                const diffX = Math.abs(e.changedTouches[0].screenX - touchStartX);
                const diffY = Math.abs(e.changedTouches[0].screenY - touchStartY);
                
                if (diffX > diffY && diffX > 10) {
                    this.isSwipping = true;
                    e.preventDefault();
                }
            }
        }, { passive: false });
        
        this.container.addEventListener('touchend', (e) => {
            if (!this.isSwipping) return;
            
            touchEndX = e.changedTouches[0].screenX;
            touchEndY = e.changedTouches[0].screenY;
            
            this.handleSwipe(touchStartX, touchEndX, touchStartY, touchEndY);
            this.isSwipping = false;
        }, { passive: true });
    }
    
    handleSwipe(startX, endX, startY, endY) {
        const threshold = 50;
        const diffX = startX - endX;
        const diffY = Math.abs(startY - endY);
        
        // Garantir que é um swipe horizontal
        if (Math.abs(diffX) > threshold && diffY < 100) {
            if (diffX > 0) {
                // Swipe left - próximo mês
                this.nextMonth();
            } else {
                // Swipe right - mês anterior
                this.previousMonth();
            }
            MobileUtils.vibrate();
        }
    }
    
    setupTouchFeedback() {
        // Adicionar feedback visual ao tocar em elementos
        this.container.addEventListener('touchstart', (e) => {
            const target = e.target.closest('.touchable');
            if (target) {
                target.classList.add('touching');
                MobileUtils.vibrate(5);
            }
        }, { passive: true });
        
        this.container.addEventListener('touchend', (e) => {
            const touching = this.container.querySelectorAll('.touching');
            touching.forEach(el => el.classList.remove('touching'));
        }, { passive: true });
    }
    
    setupPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let pulling = false;
        
        this.container.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].pageY;
                pulling = true;
            }
        }, { passive: true });
        
        this.container.addEventListener('touchmove', (e) => {
            if (!pulling) return;
            
            currentY = e.touches[0].pageY;
            const diff = currentY - startY;
            
            if (diff > 0 && window.scrollY === 0) {
                e.preventDefault();
                
                if (diff > 100) {
                    this.showRefreshIndicator();
                }
            }
        }, { passive: false });
        
        this.container.addEventListener('touchend', (e) => {
            if (!pulling) return;
            
            const diff = currentY - startY;
            if (diff > 100) {
                this.refresh();
            }
            
            pulling = false;
            this.hideRefreshIndicator();
        }, { passive: true });
    }
    
    showRefreshIndicator() {
        // Implementar indicador visual de refresh
        const indicator = document.createElement('div');
        indicator.className = 'refresh-indicator';
        indicator.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i>';
        this.container.prepend(indicator);
    }
    
    hideRefreshIndicator() {
        const indicator = this.container.querySelector('.refresh-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    async refresh() {
        MobileUtils.vibrate(20);
        await this.loadEvents();
        this.render();
    }
    
    async loadEvents() {
        try {
            const response = await fetch(`/api/calendar/events?month=${this.currentMonth.getMonth() + 1}&year=${this.currentMonth.getFullYear()}`);
            const data = await response.json();
            this.events = data.events;
        } catch (error) {
            console.error('Erro ao carregar eventos:', error);
            this.showError('Erro ao carregar eventos');
        }
    }
    
    nextMonth() {
        this.animateTransition('left', () => {
            this.currentMonth.setMonth(this.currentMonth.getMonth() + 1);
            this.render();
        });
    }
    
    previousMonth() {
        this.animateTransition('right', () => {
            this.currentMonth.setMonth(this.currentMonth.getMonth() - 1);
            this.render();
        });
    }
    
    animateTransition(direction, callback) {
        const content = this.container.querySelector('.calendar-content');
        content.style.transition = 'transform 0.3s ease-out';
        content.style.transform = `translateX(${direction === 'left' ? '-100%' : '100%'})`;
        
        setTimeout(() => {
            callback();
            content.style.transition = 'none';
            content.style.transform = `translateX(${direction === 'left' ? '100%' : '-100%'})`;
            
            setTimeout(() => {
                content.style.transition = 'transform 0.3s ease-out';
                content.style.transform = 'translateX(0)';
            }, 20);
        }, 300);
    }
    
    render() {
        // Implementar renderização do calendário
        const html = this.generateCalendarHTML();
        this.container.innerHTML = html;
        this.attachEventListeners();
    }
    
    generateCalendarHTML() {
        // Gerar HTML do calendário baseado no mês atual
        // Implementação específica do layout
        return `
            <div class="calendar-content">
                <!-- Conteúdo do calendário -->
            </div>
        `;
    }
    
    attachEventListeners() {
        // Adicionar listeners aos elementos renderizados
        const dayElements = this.container.querySelectorAll('.calendar-day');
        dayElements.forEach(day => {
            day.addEventListener('click', (e) => {
                this.selectDate(day.dataset.date);
            });
        });
    }
    
    selectDate(date) {
        this.selectedDate = date;
        MobileUtils.vibrate(10);
        this.showDateEvents(date);
    }
    
    showDateEvents(date) {
        const events = this.events.filter(e => e.date === date);
        // Mostrar modal ou expandir eventos
        this.showEventsModal(events);
    }
    
    showEventsModal(events) {
        // Implementar modal de eventos
        const modal = new MobileModal({
            title: 'Agendamentos',
            content: this.generateEventsHTML(events),
            onClose: () => {
                this.selectedDate = null;
            }
        });
        modal.show();
    }
    
    generateEventsHTML(events) {
        if (events.length === 0) {
            return '<p class="text-center text-muted">Nenhum agendamento neste dia</p>';
        }
        
        return events.map(event => `
            <div class="event-card touchable" data-event-id="${event.id}">
                <div class="event-title">${event.laboratory_name}</div>
                <div class="event-details">
                    <span><i class="bi bi-person"></i> ${event.professor_name}</span>
                    <span><i class="bi bi-book"></i> ${event.subject}</span>
                </div>
                <span class="event-status status-${event.status}"></span>
            </div>
        `).join('');
    }
    
    showError(message) {
        const toast = new MobileToast(message, 'error');
        toast.show();
    }
}

// Modal Mobile
class MobileModal {
    constructor(options) {
        this.options = {
            title: '',
            content: '',
            showClose: true,
            onClose: null,
            ...options
        };
        
        this.modal = null;
        this.backdrop = null;
        this.create();
    }
    
    create() {
        // Backdrop
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'mobile-modal-backdrop';
        
        // Modal
        this.modal = document.createElement('div');
        this.modal.className = 'mobile-modal';
        this.modal.innerHTML = `
            <div class="mobile-modal-content">
                <div class="mobile-modal-header">
                    <h5 class="mobile-modal-title">${this.options.title}</h5>
                    ${this.options.showClose ? '<button class="mobile-modal-close">&times;</button>' : ''}
                </div>
                <div class="mobile-modal-body">
                    ${this.options.content}
                </div>
            </div>
        `;
        
        // Event listeners
        this.backdrop.addEventListener('click', () => this.close());
        
        const closeBtn = this.modal.querySelector('.mobile-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        
        // Prevenir fechamento ao clicar no conteúdo
        this.modal.querySelector('.mobile-modal-content').addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }
    
    show() {
        document.body.appendChild(this.backdrop);
        document.body.appendChild(this.modal);
        
        // Animar entrada
        requestAnimationFrame(() => {
            this.backdrop.classList.add('show');
            this.modal.classList.add('show');
        });
        
        // Prevenir scroll do body
        document.body.style.overflow = 'hidden';
        
        MobileUtils.vibrate(10);
    }
    
    close() {
        this.backdrop.classList.remove('show');
        this.modal.classList.remove('show');
        
        setTimeout(() => {
            this.backdrop.remove();
            this.modal.remove();
            document.body.style.overflow = '';
            
            if (this.options.onClose) {
                this.options.onClose();
            }
        }, 300);
    }
}

// Toast Mobile
class MobileToast {
    constructor(message, type = 'info') {
        this.message = message;
        this.type = type;
        this.duration = 3000;
    }
    
    show() {
        const toast = document.createElement('div');
        toast.className = `mobile-toast mobile-toast-${this.type}`;
        toast.innerHTML = `
            <div class="mobile-toast-content">
                <i class="bi bi-${this.getIcon()}"></i>
                <span>${this.message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Animar entrada
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });
        
        // Auto remover
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, this.duration);
        
        MobileUtils.vibrate(20);
    }
    
    getIcon() {
        const icons = {
            success: 'check-circle-fill',
            error: 'exclamation-circle-fill',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle-fill'
        };
        return icons[this.type] || icons.info;
    }
}

// Componente de Lista de Agendamentos Mobile
class MobileScheduleList {
    constructor(container, options = {}) {
        this.container = container;
        this.schedules = [];
        this.filters = {
            status: 'all',
            laboratory: 'all',
            date: null
        };
        this.options = {
            onItemClick: null,
            emptyMessage: 'Nenhum agendamento encontrado',
            ...options
        };
        
        this.init();
    }
    
    init() {
        this.render();
        this.setupInfiniteScroll();
    }
    
    setupInfiniteScroll() {
        let loading = false;
        const threshold = 100;
        
        window.addEventListener('scroll', () => {
            if (loading) return;
            
            const scrollPosition = window.innerHeight + window.scrollY;
            const documentHeight = document.documentElement.offsetHeight;
            
            if (scrollPosition >= documentHeight - threshold) {
                loading = true;
                this.loadMore().then(() => {
                    loading = false;
                });
            }
        });
    }
    
    async loadMore() {
        // Simular carregamento de mais itens
        const moreItems = await this.fetchMoreSchedules();
        if (moreItems.length > 0) {
            this.schedules = [...this.schedules, ...moreItems];
            this.appendItems(moreItems);
        }
    }
    
    async fetchMoreSchedules() {
        // Implementar fetch real
        return [];
    }
    
    setFilter(filterType, value) {
        this.filters[filterType] = value;
        this.render();
    }
    
    getFilteredSchedules() {
        return this.schedules.filter(schedule => {
            if (this.filters.status !== 'all' && schedule.status !== this.filters.status) {
                return false;
            }
            if (this.filters.laboratory !== 'all' && schedule.laboratory_id != this.filters.laboratory) {
                return false;
            }
            if (this.filters.date && schedule.date !== this.filters.date) {
                return false;
            }
            return true;
        });
    }
    
    render() {
        const filteredSchedules = this.getFilteredSchedules();
        
        if (filteredSchedules.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <i class="bi bi-calendar-x empty-state-icon"></i>
                    <p>${this.options.emptyMessage}</p>
                </div>
            `;
            return;
        }
        
        this.container.innerHTML = filteredSchedules.map(schedule => 
            this.generateScheduleItemHTML(schedule)
        ).join('');
        
        this.attachEventListeners();
    }
    
    generateScheduleItemHTML(schedule) {
        const statusColors = {
            approved: 'success',
            pending: 'warning',
            rejected: 'danger'
        };
        
        const statusLabels = {
            approved: 'Aprovado',
            pending: 'Pendente',
            rejected: 'Rejeitado'
        };
        
        return `
            <div class="schedule-item-card touchable" data-schedule-id="${schedule.id}">
                <div class="schedule-item-icon">
                    <i class="bi bi-calendar3"></i>
                </div>
                <div class="schedule-item-content">
                    <div class="schedule-item-title">${schedule.laboratory_name}</div>
                    <div class="schedule-item-subtitle">
                        ${schedule.date} • ${schedule.start_time} - ${schedule.end_time}
                    </div>
                    <div class="schedule-item-subtitle">
                        <i class="bi bi-person"></i> ${schedule.professor_name}
                    </div>
                </div>
                <span class="badge bg-${statusColors[schedule.status]} schedule-item-badge">
                    ${statusLabels[schedule.status]}
                </span>
            </div>
        `;
    }
    
    appendItems(items) {
        const html = items.map(item => this.generateScheduleItemHTML(item)).join('');
        this.container.insertAdjacentHTML('beforeend', html);
        this.attachEventListeners();
    }
    
    attachEventListeners() {
        const items = this.container.querySelectorAll('.schedule-item-card');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const scheduleId = item.dataset.scheduleId;
                MobileUtils.vibrate(10);
                
                if (this.options.onItemClick) {
                    this.options.onItemClick(scheduleId);
                }
            });
        });
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    if (MobileUtils.isMobile()) {
        // Prevenir zoom
        MobileUtils.preventZoom();
        
        // Inicializar calendário mobile se existir
        const calendarContainer = document.querySelector('.mobile-calendar-container');
        if (calendarContainer) {
            window.mobileCalendar = new MobileCalendar(calendarContainer);
        }
        
        // Inicializar lista de agendamentos se existir
        const scheduleListContainer = document.querySelector('.mobile-schedule-list');
        if (scheduleListContainer) {
            window.mobileScheduleList = new MobileScheduleList(scheduleListContainer, {
                onItemClick: (scheduleId) => {
                    // Abrir detalhes do agendamento
                    console.log('Agendamento clicado:', scheduleId);
                }
            });
        }
        
        // Adicionar classe ao body para estilos específicos mobile
        document.body.classList.add('is-mobile');
        
        // Detectar mudanças de orientação
        window.addEventListener('orientationchange', () => {
            document.body.classList.toggle('is-landscape', MobileUtils.isLandscape());
        });
        
        // Smooth scroll para links internos
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
});

// Exportar para uso global
window.MobileUtils = MobileUtils;
window.MobileCalendar = MobileCalendar;
window.MobileModal = MobileModal;
window.MobileToast = MobileToast;
window.MobileScheduleList = MobileScheduleList;