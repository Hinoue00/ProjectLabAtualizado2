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
        if (!this.elements.labActivityChart) {
            this.dashboard.log('❌ Canvas element not found for lab activity chart', 'error');
            return;
        }

        const ctx = this.elements.labActivityChart.getContext('2d');
        
        // 🔧 CORREÇÃO: Configuração mais robusta do gráfico
        const config = {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 750
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'top',
                        display: true,
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        callbacks: {
                            title: function(context) {
                                return context[0].label;
                            },
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y} agendamento${context.parsed.y !== 1 ? 's' : ''}`;
                            }
                        }
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
                            color: '#e9ecef'
                        },
                        ticks: {
                            stepSize: 1,
                            color: '#6c757d'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Período'
                        },
                        grid: {
                            color: '#f8f9fa'
                        },
                        ticks: {
                            color: '#6c757d',
                            maxRotation: 45
                        }
                    }
                }
            }
        };

        // Create chart instance
        const chart = new Chart(ctx, config);
        this.charts.set('labActivity', chart);
        
        this.dashboard.log('📈 Lab Activity chart created');

        // 🔧 CORREÇÃO: Load initial data with fallback
        try {
            await this.loadChartData('week', 'all');
        } catch (error) {
            this.dashboard.log(`⚠️ Failed to load initial chart data: ${error.message}`, 'warn');
            this.showChartError('Falha ao carregar dados iniciais');
        }
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

            // 🔧 CORREÇÃO: Limpar cache se necessário
            if (period === 'month') {
                // Para month, sempre buscar dados frescos devido ao bug anterior
                const cacheKey = `chart_${period}_${department}`;
                this.chartData.delete(cacheKey);
            }

            // Check cache first
            const cacheKey = `chart_${period}_${department}`;
            let data = this.getFromCache(cacheKey);

            if (!data) {
                // Fetch from server
                data = await this.fetchChartData(period, department);
                
                // 🔧 CORREÇÃO: Validar dados antes de cachear
                if (data && data.labels && data.datasets) {
                    this.setCache(cacheKey, data);
                } else {
                    throw new Error('Dados inválidos recebidos do servidor');
                }
            } else {
                this.dashboard.log('📦 Using cached chart data');
            }

            // 🔧 CORREÇÃO: Log dos dados antes de atualizar
            this.dashboard.log(`📊 Data received:`, 'info');
            this.dashboard.log(`   Labels: ${data.labels?.length || 0}`, 'info');
            this.dashboard.log(`   Datasets: ${data.datasets?.length || 0}`, 'info');

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
        
        this.dashboard.log(`📡 Fetching chart data from: ${url}`);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            },
            credentials: 'same-origin'
        });

        this.dashboard.log(`📡 Response status: ${response.status}`);

        if (!response.ok) {
            const errorText = await response.text();
            this.dashboard.log(`❌ Server response: ${errorText}`, 'error');
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        
        // 🔧 CORREÇÃO: Log detalhado da resposta
        this.dashboard.log(`📊 Server response:`, 'info');
        this.dashboard.log(`   Labels: ${data.labels?.length || 0}`, 'info');
        this.dashboard.log(`   Datasets: ${data.datasets?.length || 0}`, 'info');
        this.dashboard.log(`   Full data:`, data);
        
        // 🔧 CORREÇÃO: Validação rigorosa dos dados
        if (!data.labels || !Array.isArray(data.labels)) {
            throw new Error('Labels inválidos recebidos do servidor');
        }
        
        if (!data.datasets || !Array.isArray(data.datasets)) {
            throw new Error('Datasets inválidos recebidos do servidor');
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

        // 🔧 CORREÇÃO: Log detalhado dos dados recebidos
        this.dashboard.log(`📊 Updating chart '${chartName}' with:`, 'info');
        this.dashboard.log(`   Labels: ${data.labels?.length || 0}`, 'info');
        this.dashboard.log(`   Datasets: ${data.datasets?.length || 0}`, 'info');
        
        // Debug dos datasets
        if (data.datasets && data.datasets.length > 0) {
            data.datasets.forEach((dataset, idx) => {
                const totalData = dataset.data.reduce((sum, val) => sum + val, 0);
                this.dashboard.log(`   Dataset ${idx}: ${dataset.label} - Total: ${totalData}`, 'info');
            });
        }

        // 🔧 CORREÇÃO: Validar dados antes de atualizar
        if (!data.labels || !Array.isArray(data.labels)) {
            this.dashboard.log(`❌ Invalid labels data`, 'error');
            this.showChartError('Dados de labels inválidos');
            return;
        }

        if (!data.datasets || !Array.isArray(data.datasets)) {
            this.dashboard.log(`❌ Invalid datasets data`, 'error');
            this.showChartError('Dados de datasets inválidos');
            return;
        }

        // 🔧 CORREÇÃO: Limpar dados anteriores explicitamente
        chart.data.labels = [];
        chart.data.datasets = [];

        // 🔧 CORREÇÃO: Atualizar dados com validação
        chart.data.labels = [...data.labels];
        chart.data.datasets = data.datasets.map(dataset => ({
            ...dataset,
            data: [...dataset.data] // Criar nova array para evitar referência
        }));

        // 🔧 CORREÇÃO: Atualizar opções do gráfico
        if (chart.options.scales) {
            // Atualizar título do eixo X
            if (chart.options.scales.x && chart.options.scales.x.title) {
                chart.options.scales.x.title.text = data.xAxisTitle || this.getXAxisTitle(period);
            }

            // 🔧 CORREÇÃO: Forçar recálculo dos eixos
            if (chart.options.scales.y) {
                // Calcular max dinâmico baseado nos dados
                const allValues = data.datasets.flatMap(d => d.data).filter(v => v !== null && v !== undefined);
                const maxValue = Math.max(...allValues, 1); // Mínimo 1 para evitar divisão por zero
                
                chart.options.scales.y.max = Math.ceil(maxValue * 1.1); // 10% acima do máximo
                chart.options.scales.y.min = 0;
            }
        }

        // 🔧 CORREÇÃO: Configurar visibilidade da legenda
        if (chart.options.plugins && chart.options.plugins.legend) {
            chart.options.plugins.legend.display = data.datasets.length > 0;
        }

        // 🔧 CORREÇÃO: Atualizar tema
        this.updateChartTheme(chart);

        // 🔧 CORREÇÃO: Forçar atualização completa com resize
        chart.update('resize');
        
        // 🔧 CORREÇÃO: Double-check após update
        setTimeout(() => {
            if (chart.data.datasets.length === 0) {
                this.dashboard.log(`⚠️ Chart still empty after update, showing fallback`, 'warn');
                this.showEmptyChartMessage(chart);
            }
        }, 100);

        this.dashboard.log(`✅ Chart '${chartName}' updated successfully`, 'success');
    }

    showEmptyChartMessage(chart) {
        // Criar dataset vazio para mostrar mensagem
        chart.data.labels = ['Sem dados'];
        chart.data.datasets = [{
            label: 'Nenhum agendamento encontrado',
            data: [0],
            borderColor: '#e9ecef',
            backgroundColor: '#f8f9fa',
            borderDash: [5, 5]
        }];
        
        chart.update('none');
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
            // Limpar dados do gráfico
            chart.data.labels = [];
            chart.data.datasets = [];
            chart.update('none');
        }

        // 🔧 CORREÇÃO: Melhor feedback visual de erro
        if (this.elements.chartContainer) {
            // Remover erros anteriores
            const existingErrors = this.elements.chartContainer.querySelectorAll('.chart-error');
            existingErrors.forEach(error => error.remove());
            
            const errorHtml = `
                <div class="chart-error alert alert-warning text-center m-3">
                    <h6><i class="bi bi-exclamation-triangle"></i> Erro no Gráfico</h6>
                    <p class="mb-2">${message}</p>
                    <button class="btn btn-sm btn-outline-secondary" onclick="window.DashboardApp?.chart?.refreshChart('labActivity')">
                        <i class="bi bi-arrow-clockwise"></i> Tentar Novamente
                    </button>
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

// ==========================================
// ADIÇÃO DE FUNÇÃO DE DEBUG NO CONSOLE
// ==========================================

// Adicione esta função para debug manual:
window.debugChart = function(period = 'month', department = 'all') {
    console.log(`🔍 DEBUGGING CHART: period=${period}, department=${department}`);
    
    if (window.DashboardApp && window.DashboardApp.chart) {
        // Limpar cache
        const cacheKey = `chart_${period}_${department}`;
        window.DashboardApp.chart.chartData.delete(cacheKey);
        
        // Recarregar dados
        window.DashboardApp.chart.loadChartData(period, department);
    } else {
        console.error('❌ DashboardApp.chart not available');
    }
};

/**
 * Export to global scope
 */
window.ChartModule = ChartModule;