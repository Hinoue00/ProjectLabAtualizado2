/* =============================================================================
   DASHBOARD MAIN - LabConnect
   Main initialization and utilities
   ============================================================================= */

/**
 * Main Dashboard Application
 */
class DashboardApp {
    constructor() {
        this.isInitialized = false;
        this.modules = new Map();
        this.cache = new Map();
        this.config = {
            debug: true,
            apiBaseUrl: '/dashboard/',
            cacheTTL: 5 * 60 * 1000, // 5 minutes
            debounceDelay: 300
        };
        
        console.log('🚀 DashboardApp initialized');
    }

    /**
     * Initialize the application
     */
    async init() {
        if (this.isInitialized) {
            console.warn('⚠️ Dashboard already initialized');
            return;
        }

        try {
            this.log('Initializing Dashboard...');
            
            // Initialize utilities
            this.initUtilities();
            
            // Wait for DOM
            if (document.readyState === 'loading') {
                await new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', resolve);
                });
            }

            // Initialize modules
            await this.initModules();
            
            // Setup global event listeners
            this.setupGlobalListeners();
            
            this.isInitialized = true;
            this.log('✅ Dashboard initialized successfully');
            
        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            throw error;
        }
    }

    /**
     * Initialize utility functions
     */
    initUtilities() {
        // Date utilities
        this.dateUtils = {
            formatDate: (isoString, format = 'pt-BR') => {
                const date = new Date(isoString + 'T00:00:00');
                return date.toLocaleDateString(format);
            },
            
            formatDateShort: (isoString) => {
                const date = new Date(isoString + 'T00:00:00');
                return date.toLocaleDateString('pt-BR', { 
                    day: '2-digit', 
                    month: '2-digit' 
                });
            },
            
            formatDateTime: (isoString) => {
                const date = new Date(isoString);
                return date.toLocaleString('pt-BR');
            }
        };

        // DOM utilities
        this.dom = {
            $(selector) {
                return document.querySelector(selector);
            },
            
            $$(selector) {
                return document.querySelectorAll(selector);
            },
            
            createElement(tag, classes = [], attributes = {}) {
                const element = document.createElement(tag);
                if (classes.length) {
                    element.classList.add(...classes);
                }
                Object.entries(attributes).forEach(([key, value]) => {
                    element.setAttribute(key, value);
                });
                return element;
            },

            showLoading(container, message = 'Carregando...') {
                const loadingHtml = `
                    <div class="d-flex justify-content-center align-items-center p-5">
                        <div class="spinner-border text-primary me-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <span>${message}</span>
                    </div>
                `;
                container.innerHTML = loadingHtml;
            },

            showError(container, message, showReload = true) {
                const reloadButton = showReload ? `
                    <button class="btn btn-outline-primary btn-sm mt-2" onclick="window.location.reload()">
                        <i class="bi bi-arrow-clockwise"></i> Recarregar página
                    </button>
                ` : '';
                
                const errorHtml = `
                    <div class="alert alert-danger text-center m-3">
                        <h5><i class="bi bi-exclamation-triangle"></i> Erro</h5>
                        <p class="mb-3">${message}</p>
                        ${reloadButton}
                    </div>
                `;
                container.innerHTML = errorHtml;
            }
        };

        // API utilities
        this.api = {
            get: async (url, options = {}) => {
                return this.makeRequest(url, { method: 'GET', ...options });
            },
            
            post: async (url, data, options = {}) => {
                return this.makeRequest(url, {
                    method: 'POST',
                    body: JSON.stringify(data),
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });
            }
        };
    }

    /**
     * Make HTTP request with error handling and caching
     */
    async makeRequest(url, options = {}) {
        const fullUrl = url.startsWith('http') ? url : `${this.config.apiBaseUrl}${url}`;
        const cacheKey = `${options.method || 'GET'}_${fullUrl}`;
        
        // Check cache for GET requests
        if (!options.method || options.method === 'GET') {
            const cached = this.getFromCache(cacheKey);
            if (cached) {
                this.log(`📦 Cache hit for ${url}`);
                return cached;
            }
        }

        try {
            this.log(`📡 Making request to: ${url}`);
            
            const response = await fetch(fullUrl, {
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Cache successful GET requests
            if (!options.method || options.method === 'GET') {
                this.setCache(cacheKey, data);
            }
            
            return data;
            
        } catch (error) {
            console.error(`❌ Request failed for ${url}:`, error);
            throw error;
        }
    }

    /**
     * Initialize modules
     */
    async initModules() {
        const modulePromises = [];

        // Calendar Module
        if (this.dom.$('#calendar-body')) {
            const CalendarModule = window.CalendarModule;
            if (CalendarModule) {
                const calendar = new CalendarModule(this);
                this.modules.set('calendar', calendar);
                modulePromises.push(calendar.init());
                this.log('📅 Calendar module registered');
            }
        }

        // Modal Module
        if (this.dom.$$('[data-bs-toggle="modal"]').length > 0) {
            const ModalModule = window.ModalModule;
            if (ModalModule) {
                const modal = new ModalModule(this);
                this.modules.set('modal', modal);
                modulePromises.push(modal.init());
                this.log('🎯 Modal module registered');
            }
        }

        // Chart Module
        if (this.dom.$('#labActivityChart')) {
            const ChartModule = window.ChartModule;
            if (ChartModule) {
                const chart = new ChartModule(this);
                this.modules.set('chart', chart);
                modulePromises.push(chart.init());
                this.log('📊 Chart module registered');
            }
        }

        // Wait for all modules to initialize
        await Promise.all(modulePromises);
        this.log('✅ All modules initialized');
    }

    /**
     * Setup global event listeners
     */
    setupGlobalListeners() {
        // Theme changes
        const themeToggle = this.dom.$('#themeToggleBtn');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => {
                setTimeout(() => {
                    this.broadcast('theme-changed', {
                        theme: document.documentElement.getAttribute('data-theme')
                    });
                }, 100);
            });
        }

        // Window resize with debounce
        window.addEventListener('resize', this.debounce(() => {
            this.broadcast('window-resized', {
                width: window.innerWidth,
                height: window.innerHeight
            });
        }, this.config.debounceDelay));

        // Unload cleanup
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
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
        if (age > this.config.cacheTTL) {
            this.cache.delete(key);
            return null;
        }
        
        return cached.data;
    }

    clearCache() {
        this.cache.clear();
        this.log('🗑️ Cache cleared');
    }

    /**
     * Event broadcasting system
     */
    broadcast(eventName, data = {}) {
        this.log(`📢 Broadcasting: ${eventName}`);
        this.modules.forEach((module, name) => {
            if (typeof module.onEvent === 'function') {
                try {
                    module.onEvent(eventName, data);
                } catch (error) {
                    console.error(`❌ Error in ${name} module event handler:`, error);
                }
            }
        });
    }

    /**
     * Utility functions
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    log(message, level = 'info') {
        if (!this.config.debug) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const prefix = `[${timestamp}] Dashboard:`;
        
        switch (level) {
            case 'error':
                console.error(`${prefix} ❌`, message);
                break;
            case 'warn':
                console.warn(`${prefix} ⚠️`, message);
                break;
            default:
                console.log(`${prefix}`, message);
        }
    }

    /**
     * Get module instance
     */
    getModule(name) {
        return this.modules.get(name);
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.log('🧹 Cleaning up dashboard');
        this.modules.forEach((module) => {
            if (typeof module.cleanup === 'function') {
                module.cleanup();
            }
        });
        this.clearCache();
    }
}

/**
 * Global Dashboard instance
 */
window.Dashboard = new DashboardApp();

/**
 * Auto-initialize when DOM is ready
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.Dashboard.init().catch(console.error);
    });
} else {
    window.Dashboard.init().catch(console.error);
}