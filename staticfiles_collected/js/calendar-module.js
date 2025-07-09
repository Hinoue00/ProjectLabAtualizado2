/* =============================================================================
   CALENDAR MODULE - LabConnect
   Handles calendar functionality and week navigation
   ============================================================================= */

/**
 * Calendar Module Class
 */
class CalendarModule {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.elements = {};
        this.state = {
            currentOffset: 0,
            currentDepartment: 'all',
            isLoading: false
        };
        this.cache = new Map();
    }

    /**
     * Initialize calendar module
     */
    async init() {
        try {
            this.dashboard.log('📅 Initializing Calendar module...');
            
            // Get DOM elements
            this.getElements();
            
            // Validate required elements
            this.validateElements();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            this.dashboard.log('✅ Calendar module initialized');
            
        } catch (error) {
            this.dashboard.log('❌ Calendar module initialization failed', 'error');
            throw error;
        }
    }

    /**
     * Get DOM elements
     */
    getElements() {
        this.elements = {
            calendarBody: this.dashboard.dom.$('#calendar-body'),
            calendarTitle: this.dashboard.dom.$('#calendar-title'),
            weekOffsetInput: this.dashboard.dom.$('#week_offset_input'),
            departmentSelect: this.dashboard.dom.$('#department-select'),
            prevWeekLink: this.dashboard.dom.$('#prev-week-link'),
            todayLink: this.dashboard.dom.$('#today-link'),
            nextWeekLink: this.dashboard.dom.$('#next-week-link')
        };

        // Debug: Log found elements
        this.dashboard.log('📋 Calendar elements found:', {
            calendarBody: !!this.elements.calendarBody,
            calendarTitle: !!this.elements.calendarTitle,
            weekOffsetInput: !!this.elements.weekOffsetInput,
            departmentSelect: !!this.elements.departmentSelect
        });
    }

    /**
     * Validate required elements
     */
    validateElements() {
        const required = ['calendarBody'];
        const missing = required.filter(key => !this.elements[key]);
        
        if (missing.length > 0) {
            throw new Error(`Missing required calendar elements: ${missing.join(', ')}`);
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Navigation buttons (using event delegation)
        document.addEventListener('click', this.handleNavigationClick.bind(this));
        
        // Department filter
        if (this.elements.departmentSelect) {
            this.elements.departmentSelect.addEventListener(
                'change', 
                this.dashboard.debounce(this.handleDepartmentChange.bind(this), 300)
            );
        }

        // Keyboard navigation
        document.addEventListener('keydown', this.handleKeyboardNav.bind(this));
    }

    /**
     * Handle navigation button clicks
     */
    handleNavigationClick(event) {
        const target = event.target.closest('a[id$="-link"]');
        if (!target) return;

        event.preventDefault();
        
        const currentOffset = this.getCurrentOffset();
        const department = this.getCurrentDepartment();
        let newOffset = currentOffset;

        switch (target.id) {
            case 'prev-week-link':
                newOffset = currentOffset - 1;
                this.dashboard.log('⬅️ Previous week clicked');
                break;
            case 'today-link':
                newOffset = 0;
                this.dashboard.log('🏠 Today clicked');
                break;
            case 'next-week-link':
                newOffset = currentOffset + 1;
                this.dashboard.log('➡️ Next week clicked');
                break;
        }

        this.loadWeekData(newOffset, department);
    }

    /**
     * Handle department filter changes
     */
    handleDepartmentChange() {
        const currentOffset = this.getCurrentOffset();
        const department = this.elements.departmentSelect.value;
        
        this.dashboard.log(`🏢 Department changed to: ${department}`);
        this.loadWeekData(currentOffset, department);
    }

    /**
     * Handle keyboard navigation
     */
    handleKeyboardNav(event) {
        // Only handle if no input is focused
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT') {
            return;
        }

        const currentOffset = this.getCurrentOffset();
        const department = this.getCurrentDepartment();

        switch (event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                this.loadWeekData(currentOffset - 1, department);
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.loadWeekData(currentOffset + 1, department);
                break;
            case 'Home':
                event.preventDefault();
                this.loadWeekData(0, department);
                break;
        }
    }

    /**
     * Load initial calendar data
     */
    async loadInitialData() {
        const offset = this.getCurrentOffset();
        const department = this.getCurrentDepartment();
        
        this.dashboard.log(`📅 Loading initial calendar data: offset=${offset}, department=${department}`);
        
        // Don't await here since the calendar might already be populated by the server
        this.loadWeekData(offset, department, false);
    }

    /**
     * Main function to load week data
     */
    async loadWeekData(weekOffset, department = 'all', showLoading = true) {
        if (this.state.isLoading) {
            this.dashboard.log('⏳ Calendar load already in progress, skipping');
            return;
        }

        try {
            this.state.isLoading = true;
            this.state.currentOffset = weekOffset;
            this.state.currentDepartment = department;

            this.dashboard.log(`📅 Loading week data: offset=${weekOffset}, department=${department}`);

            // Show loading state
            if (showLoading) {
                this.showLoadingState();
            }

            // Check cache first
            const cacheKey = `week_${weekOffset}_${department}`;
            let data = this.getFromCache(cacheKey);

            if (!data) {
                // Fetch from server
                data = await this.fetchWeekData(weekOffset, department);
                this.setCache(cacheKey, data);
            } else {
                this.dashboard.log('📦 Using cached calendar data');
            }

            // Update UI
            this.updateCalendarUI(data);
            this.updateNavigationState(weekOffset, department);

        } catch (error) {
            this.dashboard.log(`❌ Error loading week data: ${error.message}`, 'error');
            this.showErrorState(error.message);
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Fetch week data from server
     */
    async fetchWeekData(weekOffset, department) {
        const url = new URL(window.location.href);
        url.searchParams.set('week_offset', weekOffset);
        url.searchParams.set('department', department);

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success && data.success !== undefined) {
            throw new Error(data.message || 'Unknown error occurred');
        }

        return data;
    }

    /**
     * Update calendar UI with new data
     */
    updateCalendarUI(data) {
        // Update calendar body HTML
        if (data.calendar_html && this.elements.calendarBody) {
            this.elements.calendarBody.innerHTML = data.calendar_html;
            this.dashboard.log('✅ Calendar HTML updated');
            
            // Notify other modules about calendar update
            this.dashboard.broadcast('calendar-updated', { data });
        }

        // Update title
        if (data.start_of_week && data.end_of_week && this.elements.calendarTitle) {
            const startFormatted = this.dashboard.dateUtils.formatDateShort(data.start_of_week);
            const endFormatted = this.dashboard.dateUtils.formatDate(data.end_of_week);
            this.elements.calendarTitle.textContent = `Calendário Semanal (${startFormatted} - ${endFormatted})`;
            this.dashboard.log('✅ Calendar title updated');
        }
    }

    /**
     * Update navigation state
     */
    updateNavigationState(weekOffset, department) {
        // Update hidden input
        if (this.elements.weekOffsetInput) {
            this.elements.weekOffsetInput.value = weekOffset;
            this.dashboard.log(`✅ Week offset updated to: ${weekOffset}`);
        }

        // Update department select
        if (this.elements.departmentSelect) {
            this.elements.departmentSelect.value = department;
            this.dashboard.log(`✅ Department updated to: ${department}`);
        }

        // Update URL without reload
        this.updateURL(weekOffset, department);
    }

    /**
     * Update browser URL without reloading
     */
    updateURL(weekOffset, department) {
        const url = new URL(window.location.href);
        url.searchParams.set('week_offset', weekOffset);
        url.searchParams.set('department', department);
        
        window.history.replaceState({}, '', url);
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        this.dashboard.dom.showLoading(
            this.elements.calendarBody, 
            'Carregando calendário...'
        );
    }

    /**
     * Show error state
     */
    showErrorState(message) {
        this.dashboard.dom.showError(
            this.elements.calendarBody,
            `Erro ao carregar calendário: ${message}`,
            true
        );
    }

    /**
     * Get current offset from input or default
     */
    getCurrentOffset() {
        return this.elements.weekOffsetInput ? 
            parseInt(this.elements.weekOffsetInput.value) || 0 : 0;
    }

    /**
     * Get current department from select or default
     */
    getCurrentDepartment() {
        return this.elements.departmentSelect ? 
            this.elements.departmentSelect.value : 'all';
    }

    /**
     * Cache management
     */
    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;
        
        const age = Date.now() - cached.timestamp;
        const ttl = 2 * 60 * 1000; // 2 minutes for calendar data
        
        if (age > ttl) {
            this.cache.delete(key);
            return null;
        }
        
        return cached.data;
    }

    /**
     * Handle events from other modules
     */
    onEvent(eventName, data) {
        switch (eventName) {
            case 'theme-changed':
                // Calendar doesn't need special theme handling
                break;
            case 'window-resized':
                // Handle responsive behavior if needed
                this.handleResize(data);
                break;
        }
    }

    /**
     * Handle window resize
     */
    handleResize(data) {
        // Add any responsive calendar logic here
        if (data.width < 768) {
            // Mobile view adjustments
            this.dashboard.log('📱 Switched to mobile view');
        } else {
            // Desktop view adjustments
            this.dashboard.log('🖥️ Switched to desktop view');
        }
    }

    /**
     * Public API methods
     */
    
    /**
     * Navigate to specific week offset
     */
    navigateToWeek(offset) {
        const department = this.getCurrentDepartment();
        this.loadWeekData(offset, department);
    }

    /**
     * Navigate to today
     */
    navigateToToday() {
        this.navigateToWeek(0);
    }

    /**
     * Refresh current week
     */
    refresh() {
        const offset = this.getCurrentOffset();
        const department = this.getCurrentDepartment();
        
        // Clear cache for current week
        const cacheKey = `week_${offset}_${department}`;
        this.cache.delete(cacheKey);
        
        // Reload
        this.loadWeekData(offset, department);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.dashboard.log('🧹 Cleaning up Calendar module');
        this.cache.clear();
        
        // Remove event listeners if needed
        // (Most are handled by event delegation, so cleanup is minimal)
    }
}

/**
 * Export to global scope
 */
window.CalendarModule = CalendarModule;