/* ===================================== */
/* 3. AVAILABILITY-CHECKER.JS */
/* ===================================== */

/**
 * Availability Checker
 * Verifica disponibilidade em tempo real
 */
class AvailabilityChecker {
    constructor() {
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutos
        this.init();
    }

    init() {
        this.setupPeriodicCheck();
        console.log('Availability Checker initialized');
    }

    setupPeriodicCheck() {
        // Verificar disponibilidade a cada 2 minutos
        setInterval(() => {
            this.refreshAvailability();
        }, 2 * 60 * 1000);
    }

    async refreshAvailability() {
        try {
            const response = await fetch('/dashboard/api/laboratory-availability/');
            const data = await response.json();
            
            this.updateAvailabilityDisplay(data);
            this.notifyChanges(data);
        } catch (error) {
            console.error('Erro ao atualizar disponibilidade:', error);
        }
    }

    updateAvailabilityDisplay(data) {
        // Atualizar grid de disponibilidade
        if (window.ScheduleModule) {
            window.ScheduleModule.availabilityData = data;
            window.ScheduleModule.renderAvailabilityGrid();
        }

        // Atualizar indicadores específicos
        this.updateAvailabilityIndicators(data);
    }

    updateAvailabilityIndicators(data) {
        const indicators = document.querySelectorAll('.availability-indicator');
        indicators.forEach(indicator => {
            const date = indicator.closest('[data-date]')?.dataset.date;
            if (date && data.week) {
                const dayData = data.week.find(d => d.date === date);
                if (dayData) {
                    const status = this.getStatusClass(dayData);
                    indicator.className = `availability-indicator ${status}`;
                }
            }
        });
    }

    getStatusClass(dayData) {
        const available = dayData.labsAvailable || 0;
        const total = dayData.totalLabs || 0;

        if (available === 0) return 'indicator-unavailable';
        if (available === total) return 'indicator-available';
        return 'indicator-partial';
    }

    notifyChanges(newData) {
        // Comparar com dados anteriores e notificar mudanças
        const previous = this.cache.get('last-availability');
        if (previous && this.hasSignificantChanges(previous, newData)) {
            this.showChangeNotification();
        }

        this.cache.set('last-availability', newData);
    }

    hasSignificantChanges(old, newData) {
        // Implementar lógica para detectar mudanças significativas
        if (!old.week || !newData.week) return false;

        return old.week.some((oldDay, index) => {
            const newDay = newData.week[index];
            return oldDay && newDay && oldDay.labsAvailable !== newDay.labsAvailable;
        });
    }

    showChangeNotification() {
        if (window.ProfessorDashboard) {
            window.ProfessorDashboard.showNotification(
                'Disponibilidade de laboratórios foi atualizada', 
                'info'
            );
        }
    }

    async checkSpecificAvailability(labId, date) {
        const cacheKey = `${labId}-${date}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached && (Date.now() - cached.timestamp) < this.cacheTimeout) {
            return cached.data;
        }

        try {
            const response = await fetch(`/dashboard/api/laboratory/${labId}/availability/?date=${date}`);
            const data = await response.json();
            
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });

            return data;
        } catch (error) {
            console.error('Erro ao verificar disponibilidade específica:', error);
            return null;
        }
    }
}