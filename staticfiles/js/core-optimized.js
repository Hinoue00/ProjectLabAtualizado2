/*
 * LabConnect - Core Optimized JavaScript
 * Scripts principais consolidados para melhor performance
 */

(function() {
    'use strict';

    // Theme Management
    const ThemeManager = {
        init() {
            const themeToggleBtn = document.getElementById('themeToggleBtn');
            const themeIcon = document.getElementById('themeIcon');
            const html = document.documentElement;
            
            // Check for saved theme
            const savedTheme = localStorage.getItem('theme') || 'light';
            html.setAttribute('data-theme', savedTheme);
            
            // Update icon based on current theme
            this.updateIcon(savedTheme, themeIcon);
            
            // Toggle theme on click
            if (themeToggleBtn) {
                themeToggleBtn.addEventListener('click', () => {
                    const currentTheme = html.getAttribute('data-theme');
                    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
                    
                    html.setAttribute('data-theme', newTheme);
                    localStorage.setItem('theme', newTheme);
                    this.updateIcon(newTheme, themeIcon);
                });
            }
        },

        updateIcon(theme, iconElement) {
            if (!iconElement) return;
            
            if (theme === 'dark') {
                iconElement.classList.remove('bi-sun-fill');
                iconElement.classList.add('bi-moon-fill');
            } else {
                iconElement.classList.remove('bi-moon-fill');
                iconElement.classList.add('bi-sun-fill');
            }
        }
    };

    // Sidebar Management
    const SidebarManager = {
        init() {
            this.sidebar = document.getElementById('sidebar');
            this.sidebarBackdrop = document.getElementById('sidebarBackdrop');
            this.sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
            this.sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
            this.body = document.body;

            this.bindEvents();
            this.initDropdowns();
        },

        bindEvents() {
            // Toggle button (header)
            if (this.sidebarToggleBtn) {
                this.sidebarToggleBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    
                    if (window.innerWidth < 992) {
                        // Mobile
                        if (this.sidebar.classList.contains('show')) {
                            this.closeSidebar();
                        } else {
                            this.openSidebar();
                        }
                    } else {
                        // Desktop
                        this.body.classList.toggle('sidebar-collapsed');
                        localStorage.setItem('sidebarCollapsed', this.body.classList.contains('sidebar-collapsed'));
                    }
                });
            }

            // Close button (X dentro do sidebar)
            if (this.sidebarCollapseBtn) {
                this.sidebarCollapseBtn.addEventListener('click', () => {
                    this.closeSidebar();
                });
            }

            // Backdrop click
            if (this.sidebarBackdrop) {
                this.sidebarBackdrop.addEventListener('click', () => {
                    this.closeSidebar();
                });
            }

            // Close sidebar on link click (mobile)
            document.querySelectorAll('.sidebar-link').forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth < 992 && !link.classList.contains('sidebar-dropdown-toggle')) {
                        setTimeout(() => this.closeSidebar(), 300);
                    }
                });
            });

            // Handle orientation change
            window.addEventListener('orientationchange', () => {
                if (window.innerWidth < 992) {
                    this.closeSidebar();
                }
            });

            // Prevent body scroll when sidebar is open
            this.preventBodyScroll();
        },

        openSidebar() {
            this.sidebar.classList.add('show');
            this.body.style.overflow = 'hidden';
        },

        closeSidebar() {
            this.sidebar.classList.remove('show');
            this.body.style.overflow = '';
        },

        initDropdowns() {
            const dropdownToggles = document.querySelectorAll('.sidebar-dropdown-toggle');
            
            dropdownToggles.forEach(toggle => {
                toggle.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    const targetId = toggle.getAttribute('data-dropdown-target');
                    const dropdownMenu = document.getElementById(targetId);
                    
                    if (!dropdownMenu) return;
                    
                    if (dropdownMenu.classList.contains('show')) {
                        // Close
                        dropdownMenu.classList.remove('show');
                        toggle.setAttribute('aria-expanded', 'false');
                    } else {
                        // Close all others first
                        document.querySelectorAll('.sidebar-dropdown-menu.show').forEach(menu => {
                            menu.classList.remove('show');
                        });
                        document.querySelectorAll('.sidebar-dropdown-toggle[aria-expanded="true"]').forEach(t => {
                            t.setAttribute('aria-expanded', 'false');
                        });
                        
                        // Open this one
                        dropdownMenu.classList.add('show');
                        toggle.setAttribute('aria-expanded', 'true');
                    }
                });
            });
        },

        preventBodyScroll() {
            let touchStartY = 0;
            
            if (this.sidebar) {
                this.sidebar.addEventListener('touchstart', (e) => {
                    touchStartY = e.touches[0].clientY;
                });
                
                this.sidebar.addEventListener('touchmove', (e) => {
                    const touchY = e.touches[0].clientY;
                    const scrollTop = this.sidebar.scrollTop;
                    const scrollHeight = this.sidebar.scrollHeight;
                    const height = this.sidebar.clientHeight;
                    
                    const isScrollingDown = touchY < touchStartY;
                    const isScrollingUp = touchY > touchStartY;
                    
                    if ((isScrollingDown && scrollTop + height >= scrollHeight) ||
                        (isScrollingUp && scrollTop <= 0)) {
                        e.preventDefault();
                    }
                }, { passive: false });
            }
        }
    };

    // Form Utilities
    const FormUtils = {
        init() {
            this.initEmailValidation();
            this.initFormEnhancements();
        },

        initEmailValidation() {
            const emailInput = document.getElementById('registerEmail');
            if (emailInput) {
                emailInput.addEventListener('input', function() {
                    const email = this.value.trim().toLowerCase();
                    const allowedDomains = ['cogna.com.br', 'kroton.com.br'];
                    
                    let isValid = false;
                    
                    if (email && email.includes('@')) {
                        const domain = email.split('@')[1];
                        isValid = allowedDomains.some(allowedDomain => domain === allowedDomain);
                    }
                    
                    const validFeedback = this.parentNode.querySelector('.input-feedback.valid');
                    const invalidFeedback = this.parentNode.querySelector('.input-feedback.invalid');
                    
                    if (email && !isValid) {
                        this.setCustomValidity('Apenas emails corporativos são permitidos.');
                        if (validFeedback) validFeedback.style.display = 'none';
                        if (invalidFeedback) {
                            invalidFeedback.style.display = 'block';
                            invalidFeedback.textContent = 'Apenas emails corporativos são permitidos.';
                        }
                    } else {
                        this.setCustomValidity('');
                        if (email) {
                            if (validFeedback) validFeedback.style.display = 'block';
                            if (invalidFeedback) invalidFeedback.style.display = 'none';
                        } else {
                            if (validFeedback) validFeedback.style.display = 'none';
                            if (invalidFeedback) invalidFeedback.style.display = 'none';
                        }
                    }
                });
            }
        },

        initFormEnhancements() {
            // Auto-dismiss alerts after 5 seconds
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.style.opacity = '0';
                        alert.style.transition = 'opacity 0.3s ease';
                        setTimeout(() => alert.remove(), 300);
                    }
                }, 5000);
            });

            // Enhanced form validation feedback
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', function(e) {
                    const invalidInputs = form.querySelectorAll(':invalid');
                    if (invalidInputs.length > 0) {
                        invalidInputs[0].focus();
                        invalidInputs[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                });
            });
        }
    };

    // Performance Utilities
    const PerformanceUtils = {
        init() {
            this.lazyLoadImages();
            this.optimizeAnimations();
        },

        lazyLoadImages() {
            const images = document.querySelectorAll('img[data-src]');
            
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.classList.remove('lazy');
                            imageObserver.unobserve(img);
                        }
                    });
                });

                images.forEach(img => imageObserver.observe(img));
            } else {
                // Fallback for older browsers
                images.forEach(img => {
                    img.src = img.dataset.src;
                });
            }
        },

        optimizeAnimations() {
            // Reduce motion for users who prefer it
            if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                document.documentElement.style.setProperty('--transition-speed', '0s');
            }

            // Pause animations when tab is not visible
            document.addEventListener('visibilitychange', () => {
                if (document.hidden) {
                    document.body.classList.add('animations-paused');
                } else {
                    document.body.classList.remove('animations-paused');
                }
            });
        }
    };

    // Modal Utilities
    const ModalUtils = {
        init() {
            this.bindModalEvents();
        },

        bindModalEvents() {
            // Auto-focus first input in modals
            document.addEventListener('shown.bs.modal', (e) => {
                const modal = e.target;
                const firstInput = modal.querySelector('input, select, textarea');
                if (firstInput) {
                    setTimeout(() => firstInput.focus(), 100);
                }
            });

            // Handle escape key globally
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    // Close sidebar on mobile
                    if (window.innerWidth < 992 && document.getElementById('sidebar').classList.contains('show')) {
                        SidebarManager.closeSidebar();
                    }
                }
            });
        }
    };

    // Network Status
    const NetworkStatus = {
        init() {
            this.checkConnection();
            this.bindEvents();
        },

        bindEvents() {
            window.addEventListener('online', () => {
                this.showConnectionStatus(true);
            });

            window.addEventListener('offline', () => {
                this.showConnectionStatus(false);
            });
        },

        checkConnection() {
            if (!navigator.onLine) {
                this.showConnectionStatus(false);
            }
        },

        showConnectionStatus(isOnline) {
            const existingAlert = document.querySelector('.connection-alert');
            if (existingAlert) {
                existingAlert.remove();
            }

            if (!isOnline) {
                const alert = document.createElement('div');
                alert.className = 'alert alert-warning connection-alert position-fixed';
                alert.style.cssText = 'top: 70px; right: 20px; z-index: 9999; min-width: 300px;';
                alert.innerHTML = `
                    <i class="bi bi-wifi-off me-2"></i>
                    Sem conexão com a internet
                `;
                document.body.appendChild(alert);
            }
        }
    };

    // Initialize all modules when DOM is loaded
    document.addEventListener('DOMContentLoaded', () => {
        try {
            ThemeManager.init();
            SidebarManager.init();
            FormUtils.init();
            PerformanceUtils.init();
            ModalUtils.init();
            NetworkStatus.init();
            
            console.log('LabConnect Core initialized successfully');
        } catch (error) {
            console.error('Error initializing LabConnect Core:', error);
        }
    });

    // Export utilities for use in other scripts
    window.LabConnect = {
        ThemeManager,
        SidebarManager,
        FormUtils,
        PerformanceUtils,
        ModalUtils,
        NetworkStatus
    };

})();