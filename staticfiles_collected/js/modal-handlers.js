/* =============================================================================
   MODAL HANDLERS MODULE - LabConnect
   Handles all modal interactions and data population
   ============================================================================= */

/**
 * Modal Module Class
 */
class ModalModule {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.elements = {};
        this.modals = new Map();
        this.modalData = new Map();
    }

    /**
     * Initialize modal module
     */
    async init() {
        try {
            this.dashboard.log('🎯 Initializing Modal module...');
            
            // Get DOM elements
            this.getElements();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize Bootstrap modals
            this.initBootstrapModals();
            
            this.dashboard.log('✅ Modal module initialized');
            
        } catch (error) {
            this.dashboard.log('❌ Modal module initialization failed', 'error');
            throw error;
        }
    }

    /**
     * Get DOM elements
     */
    getElements() {
        // Appointment modal elements
        this.elements.appointmentModal = {
            modal: this.dashboard.dom.$('#appointmentModal'),
            professor: this.dashboard.dom.$('#modal-professor'),
            laboratory: this.dashboard.dom.$('#modal-laboratory'),
            subject: this.dashboard.dom.$('#modal-subject'),
            time: this.dashboard.dom.$('#modal-time'),
            date: this.dashboard.dom.$('#modal-date'),
            students: this.dashboard.dom.$('#modal-students'),
            materials: this.dashboard.dom.$('#modal-materials'),
            description: this.dashboard.dom.$('#modal-description'),
            statusBadge: this.dashboard.dom.$('#modal-status-badge')
        };

        // Find all modal triggers
        this.elements.modalTriggers = this.dashboard.dom.$$('[data-bs-toggle="modal"]');

        this.dashboard.log(`🔗 Found ${this.elements.modalTriggers.length} modal triggers`);
    }

    /**
     * Initialize Bootstrap modals
     */
    initBootstrapModals() {
        // Check if Bootstrap is available
        if (typeof bootstrap === 'undefined') {
            this.dashboard.log('⚠️ Bootstrap not found, using native modal handling', 'warn');
            return;
        }

        // Initialize all modals
        this.dashboard.dom.$$('.modal').forEach(modalElement => {
            const modal = new bootstrap.Modal(modalElement);
            this.modals.set(modalElement.id, modal);
        });
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Bootstrap modal events
        document.addEventListener('show.bs.modal', this.handleModalShow.bind(this));
        document.addEventListener('shown.bs.modal', this.handleModalShown.bind(this));
        document.addEventListener('hide.bs.modal', this.handleModalHide.bind(this));
        document.addEventListener('hidden.bs.modal', this.handleModalHidden.bind(this));

        // Click events for modal triggers (fallback)
        this.elements.modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', this.handleTriggerClick.bind(this));
        });

        // Keyboard events
        document.addEventListener('keydown', this.handleKeyboardEvents.bind(this));
    }

    /**
     * Handle modal show event
     */
    handleModalShow(event) {
        const modal = event.target;
        const trigger = event.relatedTarget;

        this.dashboard.log(`📅 Opening modal: ${modal.id}`);

        try {
            switch (modal.id) {
                case 'appointmentModal':
                    this.populateAppointmentModal(trigger);
                    break;
                default:
                    this.dashboard.log(`⚠️ Unknown modal: ${modal.id}`, 'warn');
            }
        } catch (error) {
            this.dashboard.log(`❌ Error populating modal: ${error.message}`, 'error');
            this.showModalError(modal, 'Erro ao carregar dados do modal');
        }
    }

    /**
     * Handle modal shown event
     */
    handleModalShown(event) {
        const modal = event.target;
        this.dashboard.log(`✅ Modal shown: ${modal.id}`);
        
        // Focus first focusable element
        const focusableElement = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (focusableElement) {
            focusableElement.focus();
        }
    }

    /**
     * Handle modal hide event
     */
    handleModalHide(event) {
        const modal = event.target;
        this.dashboard.log(`🔒 Hiding modal: ${modal.id}`);
    }

    /**
     * Handle modal hidden event
     */
    handleModalHidden(event) {
        const modal = event.target;
        this.dashboard.log(`✅ Modal hidden: ${modal.id}`);
        
        // Clean up modal data
        this.modalData.delete(modal.id);
        
        // Return focus to trigger if available
        const trigger = document.activeElement;
        if (trigger && trigger.hasAttribute('data-bs-toggle')) {
            trigger.focus();
        }
    }

    /**
     * Handle trigger click (fallback for non-Bootstrap environments)
     */
    handleTriggerClick(event) {
        const trigger = event.currentTarget;
        const targetModal = trigger.getAttribute('data-bs-target');
        
        if (!targetModal) return;
        
        // If Bootstrap is not handling this, we need to manually open
        if (!this.modals.has(targetModal.replace('#', ''))) {
            event.preventDefault();
            this.openModal(targetModal.replace('#', ''), trigger);
        }
    }

    /**
     * Handle keyboard events
     */
    handleKeyboardEvents(event) {
        // ESC key to close modals
        if (event.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                this.closeModal(openModal.id);
            }
        }
    }

    /**
     * Populate appointment modal with data
     */
    populateAppointmentModal(trigger) {
        if (!trigger) {
            throw new Error('No trigger element provided');
        }

        // Extract data from trigger attributes
        const data = this.extractAppointmentData(trigger);
        
        // Store data for later use
        this.modalData.set('appointmentModal', data);
        
        // Populate modal fields
        this.populateModalFields(data);
        
        // Setup status badge
        this.setupStatusBadge(trigger, data);
        
        this.dashboard.log('✅ Appointment modal populated', data);
    }

    /**
     * Extract appointment data from trigger element
     */
    extractAppointmentData(trigger) {
        const dataAttributes = [
            'professor', 'laboratory', 'subject', 'time', 
            'date', 'students', 'materials', 'description', 'status'
        ];

        const data = {};
        dataAttributes.forEach(attr => {
            const value = trigger.getAttribute(`data-${attr}`);
            data[attr] = value || this.getDefaultValue(attr);
        });

        return data;
    }

    /**
     * Get default value for missing data
     */
    getDefaultValue(field) {
        const defaults = {
            professor: 'Não informado',
            laboratory: 'Não informado',
            subject: 'Não informado',
            time: 'Não informado',
            date: 'Não informado',
            students: 'Não informado',
            materials: 'Não especificado',
            description: 'Sem descrição',
            status: 'Não informado'
        };

        return defaults[field] || 'N/A';
    }

    /**
     * Populate modal fields with data
     */
    populateModalFields(data) {
        const fieldMapping = [
            'professor', 'laboratory', 'subject',
            'time', 'date', 'students',
            'materials', 'description'
        ];

        fieldMapping.forEach(field => {
            const element = this.elements.appointmentModal[field];
            if (element && data[field]) {
                // Handle different element types
                if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                    element.value = data[field];
                } else {
                    element.textContent = data[field];
                }
            }
        });
    }

    /**
     * Setup status badge styling
     */
    setupStatusBadge(trigger, data) {
        const statusBadge = this.elements.appointmentModal.statusBadge;
        if (!statusBadge) return;

        // Set text
        statusBadge.textContent = data.status;
        
        // Reset classes
        statusBadge.className = 'badge';
        
        // Add appropriate status class
        const statusClass = this.getStatusClass(trigger);
        if (statusClass) {
            statusBadge.classList.add(statusClass);
        }
    }

    /**
     * Get status class from trigger element
     */
    getStatusClass(trigger) {
        if (trigger.classList.contains('status-approved')) {
            return 'bg-success';
        } else if (trigger.classList.contains('status-pending')) {
            return 'bg-warning';
        } else if (trigger.classList.contains('status-rejected')) {
            return 'bg-danger';
        }
        return 'bg-secondary';
    }

    /**
     * Show error in modal
     */
    showModalError(modal, message) {
        const modalBody = modal.querySelector('.modal-body');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="bi bi-exclamation-triangle"></i> Erro</h6>
                    <p class="mb-0">${message}</p>
                </div>
            `;
        }
    }

    /**
     * Open modal programmatically
     */
    openModal(modalId, trigger = null) {
        const modal = this.modals.get(modalId);
        if (modal) {
            modal.show();
        } else {
            // Fallback for non-Bootstrap environments
            const modalElement = this.dashboard.dom.$(`#${modalId}`);
            if (modalElement) {
                modalElement.style.display = 'block';
                modalElement.classList.add('show');
                document.body.classList.add('modal-open');
                
                // Trigger show event manually
                const event = new CustomEvent('show.bs.modal', {
                    detail: { relatedTarget: trigger }
                });
                modalElement.dispatchEvent(event);
            }
        }
    }

    /**
     * Close modal programmatically
     */
    closeModal(modalId) {
        const modal = this.modals.get(modalId);
        if (modal) {
            modal.hide();
        } else {
            // Fallback for non-Bootstrap environments
            const modalElement = this.dashboard.dom.$(`#${modalId}`);
            if (modalElement) {
                modalElement.style.display = 'none';
                modalElement.classList.remove('show');
                document.body.classList.remove('modal-open');
                
                // Trigger hide event manually
                const event = new CustomEvent('hide.bs.modal');
                modalElement.dispatchEvent(event);
            }
        }
    }

    /**
     * Get modal data
     */
    getModalData(modalId) {
        return this.modalData.get(modalId);
    }

    /**
     * Update modal content
     */
    updateModalContent(modalId, newData) {
        const currentData = this.modalData.get(modalId);
        const updatedData = { ...currentData, ...newData };
        
        this.modalData.set(modalId, updatedData);
        
        if (modalId === 'appointmentModal') {
            this.populateModalFields(updatedData);
        }
        
        this.dashboard.log(`✅ Modal ${modalId} content updated`);
    }

    /**
     * Handle events from other modules
     */
    onEvent(eventName, data) {
        switch (eventName) {
            case 'calendar-updated':
                // Re-setup modal triggers for new calendar content
                this.refreshModalTriggers();
                break;
            case 'theme-changed':
                // Update modal themes if needed
                this.updateModalThemes(data.theme);
                break;
        }
    }

    /**
     * Refresh modal triggers after calendar update
     */
    refreshModalTriggers() {
        // Get new modal triggers
        const triggers = this.dashboard.dom.$$('[data-bs-toggle="modal"]');
        
        // Converter para array se necessário
        this.elements.modalTriggers = Array.from(triggers || []);
        
        // Add event listeners to new triggers
        this.elements.modalTriggers.forEach(trigger => {
            if (trigger && typeof trigger.addEventListener === 'function') {
                // Remove existing listener first (prevent duplicates)
                trigger.removeEventListener('click', this.handleTriggerClick.bind(this));
                trigger.addEventListener('click', this.handleTriggerClick.bind(this));
            }
        });
        
        this.dashboard.log(`🔄 Refreshed ${this.elements.modalTriggers.length} modal triggers`);
    }

    /**
     * Update modal themes
     */
    updateModalThemes(theme) {
        this.dashboard.dom.$('.modal').forEach(modal => {
            if (theme === 'dark') {
                modal.classList.add('modal-dark');
            } else {
                modal.classList.remove('modal-dark');
            }
        });
    }

    /**
     * Validate modal data
     */
    validateModalData(data) {
        const requiredFields = ['professor', 'laboratory', 'date', 'time'];
        const missingFields = requiredFields.filter(field => !data[field] || data[field] === 'Não informado');
        
        if (missingFields.length > 0) {
            this.dashboard.log(`⚠️ Missing modal data fields: ${missingFields.join(', ')}`, 'warn');
            return false;
        }
        
        return true;
    }

    /**
     * Create modal programmatically
     */
    createModal(config) {
        const modalHtml = `
            <div class="modal fade" id="${config.id}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered ${config.size || ''}">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${config.title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${config.content}
                        </div>
                        ${config.footer ? `<div class="modal-footer">${config.footer}</div>` : ''}
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Initialize new modal
        if (typeof bootstrap !== 'undefined') {
            const modalElement = this.dashboard.dom.$(`#${config.id}`);
            const modal = new bootstrap.Modal(modalElement);
            this.modals.set(config.id, modal);
        }
        
        this.dashboard.log(`✅ Modal ${config.id} created`);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.dashboard.log('🧹 Cleaning up Modal module');
        
        // Clear stored data
        this.modalData.clear();
        
        // Dispose Bootstrap modals
        this.modals.forEach((modal, id) => {
            if (typeof modal.dispose === 'function') {
                modal.dispose();
            }
        });
        this.modals.clear();
    }
}

/**
 * Export to global scope
 */
window.ModalModule = ModalModule;