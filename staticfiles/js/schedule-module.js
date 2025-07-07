/* ===================================== */
/* 2. SCHEDULE-MODULE.JS */
/* ===================================== */

/**
 * Schedule Module
 * Gerencia funcionalidades de agendamento
 */
class ScheduleModule {
    constructor() {
        this.selectedLab = null;
        this.selectedDate = null;
        this.selectedTime = null;
        this.availabilityData = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadAvailability();
        console.log('Schedule Module initialized');
    }

    bindEvents() {
        // Event listeners para slots de disponibilidade
        document.addEventListener('click', (e) => {
            if (e.target.matches('.availability-slot') || e.target.closest('.availability-slot')) {
                this.handleSlotClick(e);
            }

            if (e.target.matches('.schedule-form-submit')) {
                this.handleFormSubmit(e);
            }
        });

        // Formulário de agendamento
        const scheduleForm = document.querySelector('#scheduleForm');
        if (scheduleForm) {
            scheduleForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Mudanças nos campos do formulário
        document.addEventListener('change', (e) => {
            if (e.target.matches('#laboratory_select')) {
                this.handleLabChange(e);
            }
            if (e.target.matches('#date_select')) {
                this.handleDateChange(e);
            }
        });
    }

    async loadAvailability() {
        try {
            const response = await fetch('/dashboard/api/laboratory-availability/');
            this.availabilityData = await response.json();
            this.renderAvailabilityGrid();
        } catch (error) {
            console.error('Erro ao carregar disponibilidade:', error);
        }
    }

    renderAvailabilityGrid() {
        const container = document.querySelector('.availability-grid');
        if (!container || !this.availabilityData.week) return;

        const slotsHTML = this.availabilityData.week.map(day => {
            const status = this.getAvailabilityStatus(day);
            return `
                <div class="availability-slot ${status.class}" 
                     data-date="${day.date}" 
                     data-labs-available="${day.labsAvailable}"
                     tabindex="0" role="button" aria-label="Disponibilidade para ${day.dayName}">
                    <div class="slot-day">${day.dayName}</div>
                    <div class="slot-date">${day.dateFormatted}</div>
                    <div class="slot-status">
                        <span class="availability-indicator ${status.indicatorClass}"></span>
                        ${status.text}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = slotsHTML;
    }

    getAvailabilityStatus(day) {
        const total = day.totalLabs || 0;
        const available = day.labsAvailable || 0;

        if (available === 0) {
            return {
                class: 'unavailable',
                indicatorClass: 'indicator-unavailable',
                text: 'Indisponível'
            };
        } else if (available === total) {
            return {
                class: 'available',
                indicatorClass: 'indicator-available',
                text: 'Disponível'
            };
        } else {
            return {
                class: 'partial',
                indicatorClass: 'indicator-partial',
                text: `${available}/${total} disponível`
            };
        }
    }

    handleSlotClick(e) {
        const slot = e.target.closest('.availability-slot');
        if (!slot || slot.classList.contains('unavailable')) return;

        // Remove seleção anterior
        document.querySelectorAll('.availability-slot.selected').forEach(s => {
            s.classList.remove('selected');
        });

        // Adiciona seleção atual
        slot.classList.add('selected');
        this.selectedDate = slot.dataset.date;

        // Abrir modal de agendamento ou navegar para página
        this.openScheduleModal(this.selectedDate);
    }

    openScheduleModal(date = null) {
        const modal = document.querySelector('#scheduleModal');
        if (modal) {
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();

            if (date) {
                this.prefillDate(date);
            }
        } else {
            // Navegar para página de agendamento
            const url = date ? `/schedule/create/?date=${date}` : '/schedule/create/';
            window.location.href = url;
        }
    }

    prefillDate(date) {
        const dateInput = document.querySelector('#date_select');
        if (dateInput) {
            dateInput.value = date;
            this.handleDateChange({ target: dateInput });
        }
    }

    async handleLabChange(e) {
        const labId = e.target.value;
        if (!labId) return;

        try {
            const response = await fetch(`/dashboard/api/laboratory/${labId}/availability/`);
            const data = await response.json();
            this.updateTimeSlots(data.timeSlots);
        } catch (error) {
            console.error('Erro ao carregar horários:', error);
        }
    }

    handleDateChange(e) {
        const date = e.target.value;
        if (!date) return;

        this.selectedDate = date;
        this.checkConflicts();
    }

    async checkConflicts() {
        if (!this.selectedDate || !this.selectedLab) return;

        try {
            const response = await fetch('/dashboard/api/schedule-conflict-check/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    laboratory: this.selectedLab,
                    date: this.selectedDate,
                    start_time: this.selectedTime?.start,
                    end_time: this.selectedTime?.end
                })
            });

            const data = await response.json();
            this.displayConflictWarning(data.hasConflict, data.conflicts);
        } catch (error) {
            console.error('Erro ao verificar conflitos:', error);
        }
    }

    displayConflictWarning(hasConflict, conflicts = []) {
        const warningContainer = document.querySelector('.conflict-warning');
        if (!warningContainer) return;

        if (hasConflict) {
            const conflictList = conflicts.map(c => 
                `<li>${c.professor} - ${c.time}</li>`
            ).join('');

            warningContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i>
                    <strong>Conflito detectado!</strong>
                    <p>Já existem agendamentos para este horário:</p>
                    <ul>${conflictList}</ul>
                </div>
            `;
            warningContainer.style.display = 'block';
        } else {
            warningContainer.style.display = 'none';
        }
    }

    updateTimeSlots(timeSlots) {
        const container = document.querySelector('.time-slots-container');
        if (!container) return;

        const slotsHTML = timeSlots.map(slot => `
            <div class="time-slot ${slot.available ? 'available' : 'unavailable'}" 
                 data-start="${slot.start}" 
                 data-end="${slot.end}">
                <span class="time-range">${slot.start} - ${slot.end}</span>
                <span class="slot-status">${slot.available ? 'Disponível' : 'Ocupado'}</span>
            </div>
        `).join('');

        container.innerHTML = slotsHTML;
    }

    async handleFormSubmit(e) {
        e.preventDefault();
        
        const form = e.target.closest('form');
        const formData = new FormData(form);
        
        // Validar campos obrigatórios
        if (!this.validateForm(formData)) {
            return;
        }

        // Mostrar loading
        this.showFormLoading(true);

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccessMessage('Agendamento solicitado com sucesso!');
                this.closeModal();
                this.refreshPage();
            } else {
                this.showErrorMessage(result.message || 'Erro ao processar solicitação');
            }
        } catch (error) {
            console.error('Erro ao enviar formulário:', error);
            this.showErrorMessage('Erro de conexão. Tente novamente.');
        } finally {
            this.showFormLoading(false);
        }
    }

    validateForm(formData) {
        const required = ['laboratory', 'scheduled_date', 'start_time', 'end_time', 'subject'];
        const missing = required.filter(field => !formData.get(field));

        if (missing.length > 0) {
            this.showErrorMessage(`Campos obrigatórios: ${missing.join(', ')}`);
            return false;
        }

        return true;
    }

    showFormLoading(show) {
        const submitBtn = document.querySelector('.schedule-form-submit');
        const spinner = document.querySelector('.loading-spinner');

        if (submitBtn) {
            submitBtn.disabled = show;
            submitBtn.innerHTML = show ? 
                '<span class="spinner-border spinner-border-sm me-2"></span>Processando...' : 
                'Enviar Solicitação';
        }
    }

    showSuccessMessage(message) {
        if (window.ProfessorDashboard) {
            window.ProfessorDashboard.showNotification(message, 'success');
        }
    }

    showErrorMessage(message) {
        if (window.ProfessorDashboard) {
            window.ProfessorDashboard.showNotification(message, 'danger');
        }
    }

    closeModal() {
        const modal = document.querySelector('#scheduleModal');
        if (modal) {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        }
    }

    refreshPage() {
        setTimeout(() => {
            window.location.reload();
        }, 2000);
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}
