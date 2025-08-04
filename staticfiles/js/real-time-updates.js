/**
 * Sistema de Atualizações em Tempo Real para LabConnect
 * Otimizado para performance máxima em produção
 */

class RealTimeUpdater {
    constructor() {
        this.updateInterval = null;
        this.isUpdating = false;
        this.pendingUpdates = new Set();
        this.lastUpdate = Date.now();
        this.updateFrequency = 10000; // 10 segundos
        this.retryCount = 0;
        this.maxRetries = 3;
        
        this.init();
    }
    
    init() {
        // Inicializar apenas se estiver em páginas relevantes
        const relevantPages = [
            'pending_approvals',
            'pending_requests', 
            'technician_dashboard',
            'professor_dashboard'
        ];
        
        const currentPath = window.location.pathname;
        const isRelevantPage = relevantPages.some(page => 
            currentPath.includes(page) || document.body.classList.contains(page)
        );
        
        if (isRelevantPage) {
            this.startPolling();
            this.setupEventListeners();
            this.setupVisibilityHandler();
        }
    }
    
    startPolling() {
        // Usar polling inteligente - só quando a página está visível
        this.updateInterval = setInterval(() => {
            if (!document.hidden && !this.isUpdating) {
                this.checkForUpdates();
            }
        }, this.updateFrequency);
    }
    
    stopPolling() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    setupVisibilityHandler() {
        // Parar/iniciar polling baseado na visibilidade da página
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                // Verificar imediatamente quando volta a ficar visível
                this.checkForUpdates();
                this.startPolling();
            }
        });
    }
    
    setupEventListeners() {
        // Interceptar formulários de aprovação/rejeição
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.matches('[data-realtime-update]') || 
                form.querySelector('input[name="action"]')) {
                
                this.handleFormSubmit(form, e);
            }
        });
        
        // Interceptar cliques em botões de ação
        document.addEventListener('click', (e) => {
            const button = e.target.closest('button[type="submit"]');
            if (button && button.name === 'action') {
                this.markForUpdate(button.value);
            }
        });
    }
    
    handleFormSubmit(form, event) {
        // Prevenir submit normal se AJAX estiver habilitado
        if (form.dataset.ajax === 'true') {
            event.preventDefault();
            this.submitFormAjax(form);
        } else {
            // Para submits normais, fazer update após um pequeno delay
            setTimeout(() => {
                this.checkForUpdates();
            }, 1000);
        }
    }
    
    async submitFormAjax(form) {
        if (this.isUpdating) return;
        
        this.isUpdating = true;
        const submitButton = form.querySelector('button[type="submit"]:focus') || 
                           form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        
        try {
            // Mostrar feedback visual
            submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Processando...';
            submitButton.disabled = true;
            
            const formData = new FormData(form);
            const response = await fetch(form.action || window.location.pathname, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                
                if (result.success) {
                    // Sucesso - atualizar UI
                    this.showSuccessMessage(result.message || 'Operação realizada com sucesso!');
                    
                    // Remover o item processado da lista
                    const cardElement = form.closest('.card, .user-card, .request-card');
                    if (cardElement) {
                        this.animateAndRemove(cardElement);
                    }
                    
                    // Atualizar contadores
                    this.updateCounters();
                    
                } else {
                    this.showErrorMessage(result.error || 'Erro ao processar solicitação');
                }
                
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
            
        } catch (error) {
            console.error('Erro AJAX:', error);
            this.showErrorMessage('Erro de conexão. Tente novamente.');
            
            // Fallback para submit normal
            form.submit();
            
        } finally {
            // Restaurar botão
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
            this.isUpdating = false;
        }
    }
    
    async checkForUpdates() {
        if (this.isUpdating) return;
        
        try {
            const timestamp = Date.now();
            const url = new URL(window.location);
            url.searchParams.set('ajax_check', '1');
            url.searchParams.set('last_update', this.lastUpdate);
            
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.has_updates) {
                    this.processUpdates(data);
                    this.lastUpdate = timestamp;
                }
                
                this.retryCount = 0; // Reset retry count on success
            }
            
        } catch (error) {
            console.error('Erro ao verificar atualizações:', error);
            this.handleUpdateError();
        }
    }
    
    processUpdates(data) {
        // Atualizar contadores
        if (data.counters) {
            this.updateCountersFromData(data.counters);
        }
        
        // Atualizar listas
        if (data.new_items) {
            this.addNewItems(data.new_items);
        }
        
        if (data.removed_items) {
            this.removeItems(data.removed_items);
        }
        
        // Mostrar notificação se necessário
        if (data.notification) {
            this.showUpdateNotification(data.notification);
        }
    }
    
    updateCounters() {
        // Atualizar badges de contagem
        const badges = document.querySelectorAll('[data-counter]');
        badges.forEach(badge => {
            const currentCount = parseInt(badge.textContent) || 0;
            if (currentCount > 0) {
                badge.textContent = Math.max(0, currentCount - 1);
            }
        });
        
        // Atualizar títulos de página
        const pendingCount = document.querySelectorAll('.pending-item, .user-card, .request-card').length;
        document.title = document.title.replace(/\(\d+\)/, pendingCount > 0 ? `(${pendingCount})` : '');
    }
    
    updateCountersFromData(counters) {
        Object.entries(counters).forEach(([key, value]) => {
            const elements = document.querySelectorAll(`[data-counter="${key}"]`);
            elements.forEach(el => {
                el.textContent = value;
                
                // Animar mudança
                el.classList.add('counter-updated');
                setTimeout(() => el.classList.remove('counter-updated'), 500);
            });
        });
    }
    
    animateAndRemove(element) {
        element.style.transition = 'all 0.3s ease-out';
        element.style.transform = 'translateX(100%)';
        element.style.opacity = '0';
        
        setTimeout(() => {
            element.remove();
            this.checkEmptyState();
        }, 300);
    }
    
    checkEmptyState() {
        const containers = document.querySelectorAll('[data-empty-message]');
        containers.forEach(container => {
            const items = container.querySelectorAll('.user-card, .request-card, .pending-item');
            if (items.length === 0) {
                const emptyMessage = container.dataset.emptyMessage || 'Nenhum item pendente';
                container.innerHTML = `
                    <div class="empty-state text-center py-5">
                        <i class="bi bi-check-circle display-4 text-success"></i>
                        <h4 class="mt-3">${emptyMessage}</h4>
                        <p class="text-muted">Todas as solicitações foram processadas.</p>
                    </div>
                `;
            }
        });
    }
    
    showSuccessMessage(message) {
        this.showToast(message, 'success');
    }
    
    showErrorMessage(message) {
        this.showToast(message, 'error');
    }
    
    showUpdateNotification(message) {
        this.showToast(message, 'info');
    }
    
    showToast(message, type = 'info') {
        // Criar toast se não existir
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        const toastId = `toast_${Date.now()}`;
        const iconClass = {
            success: 'bi-check-circle text-success',
            error: 'bi-x-circle text-danger',
            info: 'bi-info-circle text-info'
        }[type] || 'bi-info-circle text-info';
        
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center border-0';
        toast.id = toastId;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi ${iconClass} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Mostrar toast usando Bootstrap
        const bsToast = new bootstrap.Toast(toast, { delay: 4000 });
        bsToast.show();
        
        // Remover após ocultar
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
    
    markForUpdate(action) {
        this.pendingUpdates.add(action);
    }
    
    handleUpdateError() {
        this.retryCount++;
        
        if (this.retryCount >= this.maxRetries) {
            // Reduzir frequência após muitos erros
            this.updateFrequency = Math.min(30000, this.updateFrequency * 1.5);
            this.retryCount = 0;
        }
    }
}

// CSS para animações
const style = document.createElement('style');
style.textContent = `
    .counter-updated {
        animation: counterPulse 0.5s ease-in-out;
    }
    
    @keyframes counterPulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.2); background-color: var(--success-color, #28a745); color: white; }
        100% { transform: scale(1); }
    }
    
    .toast-container .toast {
        background-color: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
    }
    
    .empty-state {
        animation: fadeIn 0.5s ease-in-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

// Inicializar quando o DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.realTimeUpdater = new RealTimeUpdater();
    });
} else {
    window.realTimeUpdater = new RealTimeUpdater();
}

// Exportar para uso global
window.RealTimeUpdater = RealTimeUpdater;