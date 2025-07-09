/* =============================================================================
   CHART MODULE - LabConnect
   Handles Chart.js integration and data visualization
   ============================================================================= */

/**
 * Chart Module Class
 */
class ChartModule {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.elements = {};
        this.charts = new Map();
        this.chartData = new Map();
        this.config = {
            animationDuration: 750,
            responsive: true,
            maintainAspectRatio: false
        };
    }

    /**
     * Initialize chart module
     */
    async init() {
        try {
            this.dashboard.log('📊 Initializing Chart module...');
            
            // Check if Chart.js is available
            this.validateChartJS();
            
            // Get DOM elements
            this.getElements();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize charts
            await this.initializeCharts();
            
            this.dashboard.log('✅ Chart module initialized');
            
        } catch (error) {
            this.dashboard.log('❌ Chart module initialization failed', 'error');
            throw error;
        }
    }

    /**
     * Validate Chart.js availability
     */
    validateChartJS() {
        if (typeof Chart === 'undefined') {
            throw new Error('Chart.js library not found. Please include Chart.js before this module.');
        }
        
        this.dashboard.log('✅ Chart.js detected');
    }

    /**
     * Get DOM elements
     */
    getElements() {
        this.elements = {
            labActivityChart: this.dashboard.dom.$('#labActivityChart'),
            chartContainer: this.dashboard.dom.$('.chart-container'),
            periodButtons: this.dashboard.dom.$$('#labActivityPeriod button'),
            departmentFilter: this.dashboard.dom.$('#chartDepartmentFilter')
        };

        // Debug: Log found elements
        this.dashboard.log('📋 Chart elements found:', {
            labActivityChart: !!this.elements.labActivityChart,
            chartContainer: !!this.elements.chartContainer,
            periodButtons: this.elements.periodButtons.length,
            departmentFilter: !!this.elements.departmentFilter
        });
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Period filter buttons
        this.elements.periodButtons.forEach(button => {
            button.addEventListener('click', this.handlePeriodChange.bind(this));
        });

        // Department filter
        if (this.elements.departmentFilter) {
            this.elements.departmentFilter.addEventListener(
                'change',
                this.dashboard.debounce(this.handleDepartmentFilterChange.bind(this), 300)
            );
        }
    }

    /**
     * Initialize all charts
     */
    async initializeCharts() {
        if (this.elements.labActivityChart) {
            await this.initLabActivityChart();
        }
    }

    /**
     * Initialize Lab Activity Chart
     */
    async initLabActivityChart() {
        const ctx = this.elements.labActivityChart.getContext('2d');
        
        // Default chart configuration
        const config = {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: this.getChartOptions('week')
        };

        // Create chart instance
        const chart = new Chart(ctx, config);
        this.charts.set('labActivity', chart);
        
        this.dashboard.log('📈 Lab Activity chart created');

        // Load initial data
        await this.loadChartData('week', 'all');
    }

    /**
     * Get chart options based on period
     */
    getChartOptions(period) {
        const baseOptions = {
            responsive: this.config.responsive,
            maintainAspectRatio: this.config.maintainAspectRatio,
            animation: {
                duration: this.config.animationDuration
            },
            plugins: {
                legend: {
                    position: 'top',
                    display: true,
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: '#ddd',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Número de Agendamentos'
                    },
                    grid: {
                        color: this.getGridColor()
                    },
                    ticks: {
                        color: this.getTickColor()
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: this.getXAxisTitle(period)
                    },
                    grid: {
                        color: this.getGridColor()
                    },
                    ticks: {
                        color: this.getTickColor()
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        };

        return baseOptions;
    }

    /**
     * Get X-axis title based on period
     */
    getXAxisTitle(period) {
        const titles = {
            week: 'Dias da Semana',
            month: 'Semanas do Mês',
            year: 'Meses do Ano'
        };
        return titles[period] || 'Período';
    }

    /**
     * Get grid color based on theme
     */
    getGridColor() {
        const theme = document.documentElement.getAttribute('data-theme');
        return theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    }

    /**
     * Get tick color based on theme
     */
    getTickColor() {
        const theme = document.documentElement.getAttribute('data-theme');
        return theme === 'dark' ? '#adb5bd' : '#6c757d';
    }

    /**
     * Handle period change
     */
    handlePeriodChange(event) {
        const button = event.currentTarget;
        const period = button.dataset.period;
        
        if (!period) {
            this.dashboard.log('⚠️ Period not found in button dataset', 'warn');
            return;
        }

        // Update active button
        this.updateActiveButton(button);
        
        // Get current department filter
        const department = this.elements.departmentFilter ? 
            this.elements.departmentFilter.value : 'all';
        
        this.dashboard.log(`📊 Period changed to: ${period}`);
        
        // Load new chart data
        this.loadChartData(period, department);
    }

    /**
     * Handle department filter change
     */
    handleDepartmentFilterChange() {
        const department = this.elements.departmentFilter.value;
        
        // Get current active period
        const activeButton = this.dashboard.dom.$('#labActivityPeriod button.active');
        const period = activeButton ? activeButton.dataset.period : 'week';
        
        this.dashboard.log(`🏢 Department filter changed to: ${department}`);
        
        // Load new chart data
        this.loadChartData(period, department);
    }

    /**
     * Update active button styling
     */
    updateActiveButton(activeButton) {
        // Remove active class from all buttons
        this.elements.periodButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Add active class to clicked button
        activeButton.classList.add('active');
    }

    /**
     * Load chart data from server
     */
    async loadChartData(period = 'week', department = 'all') {
        try {
            // Show loading state
            this.showChartLoading();
            
            this.dashboard.log(`📊 Loading chart data: period=${period}, department=${department}`);

            // Check cache first
            const cacheKey = `chart_${period}_${department}`;
            let data = this.getFromCache(cacheKey);

            if (!data) {
                // Fetch from server
                data = await this.fetchChartData(period, department);
                this.setCache(cacheKey, data);
            } else {
                this.dashboard.log('📦 Using cached chart data');
            }

            // Update chart
            this.updateChart('labActivity', data, period);

        } catch (error) {
            this.dashboard.log(`❌ Error loading chart data: ${error.message}`, 'error');
            this.showChartError(error.message);
        } finally {
            this.hideChartLoading();
        }
    }

    /**
     * Fetch chart data from server
     */
    async fetchChartData(period, department) {
        const url = `/dashboard/chart-data/?period=${period}&department=${department}`;
        
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
        
        if (!data.labels || !data.datasets) {
            throw new Error('Invalid chart data format received');
        }

        return data;
    }

    /**
     * Update chart with new data
     */
    updateChart(chartName, data, period) {
        const chart = this.charts.get(chartName);
        if (!chart) {
            this.dashboard.log(`❌ Chart '${chartName}' not found`, 'error');
            return;
        }

        // Update chart data
        chart.data.labels = data.labels;
        chart.data.datasets = data.datasets;

        // Update chart options
        chart.options.scales.x.title.text = data.xAxisTitle || this.getXAxisTitle(period);
        chart.options.plugins.legend.display = data.datasets.length > 0;

        // Update colors for current theme
        this.updateChartTheme(chart);

        // Animate chart update
        chart.update('resize');

        this.dashboard.log(`✅ Chart '${chartName}' updated with ${data.datasets.length} datasets`);
    }

    /**
     * Update chart theme colors
     */
    updateChartTheme(chart) {
        const gridColor = this.getGridColor();
        const tickColor = this.getTickColor();

        // Update grid colors
        chart.options.scales.x.grid.color = gridColor;
        chart.options.scales.y.grid.color = gridColor;

        // Update tick colors
        chart.options.scales.x.ticks.color = tickColor;
        chart.options.scales.y.ticks.color = tickColor;
    }

    /**
     * Show chart loading state
     */
    showChartLoading() {
        if (this.elements.chartContainer) {
            this.elements.chartContainer.classList.add('loading');
        }
    }

    /**
     * Hide chart loading state
     */
    hideChartLoading() {
        if (this.elements.chartContainer) {
            this.elements.chartContainer.classList.remove('loading');
        }
    }

    /**
     * Show chart error
     */
    showChartError(message) {
        const chart = this.charts.get('labActivity');
        if (chart) {
            chart.data.labels = [];
            chart.data.datasets = [];
            chart.update();
        }

        // Show error message
        if (this.elements.chartContainer) {
            const errorHtml = `
                <div class="alert alert-warning text-center m-3">
                    <h6><i class="bi bi-exclamation-triangle"></i> Erro no Gráfico</h6>
                    <p class="mb-0">${message}</p>
                </div>
            `;
            this.elements.chartContainer.insertAdjacentHTML('beforeend', errorHtml);
        }
    }

    /**
     * Cache management
     */
    setCache(key, data) {
        this.chartData.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    getFromCache(key) {
        const cached = this.chartData.get(key);
        if (!cached) return null;
        
        const age = Date.now() - cached.timestamp;
        const ttl = 5 * 60 * 1000; // 5 minutes for chart data
        
        if (age > ttl) {
            this.chartData.delete(key);
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
                this.updateAllChartsTheme();
                break;
            case 'window-resized':
                this.resizeCharts();
                break;
        }
    }

    /**
     * Update all charts theme
     */
    updateAllChartsTheme() {
        this.dashboard.log('🎨 Updating charts theme');
        
        this.charts.forEach((chart, name) => {
            this.updateChartTheme(chart);
            chart.update('none'); // Update without animation
        });
    }

    /**
     * Resize all charts
     */
    resizeCharts() {
        this.charts.forEach((chart, name) => {
            chart.resize();
        });
    }

    /**
     * Export chart as image
     */
    exportChart(chartName, filename = 'chart.png') {
        const chart = this.charts.get(chartName);
        if (!chart) {
            this.dashboard.log(`❌ Chart '${chartName}' not found for export`, 'error');
            return;
        }

        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = filename;
        link.href = url;
        link.click();

        this.dashboard.log(`📸 Chart '${chartName}' exported as ${filename}`);
    }

    /**
     * Refresh current chart data
     */
    refreshChart(chartName) {
        if (chartName === 'labActivity') {
            // Get current filters
            const activeButton = this.dashboard.dom.$('#labActivityPeriod button.active');
            const period = activeButton ? activeButton.dataset.period : 'week';
            const department = this.elements.departmentFilter ? 
                this.elements.departmentFilter.value : 'all';

            // Clear cache and reload
            const cacheKey = `chart_${period}_${department}`;
            this.chartData.delete(cacheKey);
            this.loadChartData(period, department);
        }
    }

    /**
     * Destroy chart
     */
    destroyChart(chartName) {
        const chart = this.charts.get(chartName);
        if (chart) {
            chart.destroy();
            this.charts.delete(chartName);
            this.dashboard.log(`🗑️ Chart '${chartName}' destroyed`);
        }
    }

    /**
     * Get chart instance
     */
    getChart(chartName) {
        return this.charts.get(chartName);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.dashboard.log('🧹 Cleaning up Chart module');
        
        // Destroy all charts
        this.charts.forEach((chart, name) => {
            chart.destroy();
        });
        this.charts.clear();
        
        // Clear cache
        this.chartData.clear();
    }
}

/**
 * Export to global scope
 */
window.ChartModule = ChartModule;