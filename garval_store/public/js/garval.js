/**
 * GARVAL STORE - Main JavaScript
 * E-commerce functionality with bilingual support
 */

(function() {
"use strict";

// Run immediately (before DOMContentLoaded) to catch elements early
(function() {
    // Check if we're on stripe_checkout page
    if (window.location.pathname.includes('stripe_checkout') || 
        window.location.href.includes('stripe_checkout') ||
        document.body && document.body.getAttribute('data-path') === 'stripe_checkout') {
        
        // Add class to body immediately
        if (document.body) {
            document.body.classList.add('stripe-checkout-page');
        }
        
        // Function to hide elements
        const hideElements = function() {
            // Find all possible navbar elements
            const navbars = document.querySelectorAll('.navbar, nav.navbar, nav');
            const pageHeaderWrappers = document.querySelectorAll('.page-header-wrapper');
            const pageBreadcrumbs = document.querySelectorAll('.page-breadcrumbs');
            
            // Hide all navbars
            navbars.forEach(function(navbar) {
                if (navbar) {
                    navbar.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important; opacity: 0 !important;';
                }
            });
            
            // Hide page header wrappers
            pageHeaderWrappers.forEach(function(wrapper) {
                if (wrapper) {
                    wrapper.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important; opacity: 0 !important;';
                }
            });
            
            // Hide breadcrumbs
            pageBreadcrumbs.forEach(function(breadcrumb) {
                if (breadcrumb) {
                    breadcrumb.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important;';
                }
            });
        };
        
        // Try to hide immediately if body exists
        if (document.body) {
            hideElements();
        }
        
        // Also run when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', hideElements);
        } else {
            hideElements();
        }
        
        // Run multiple times to catch any dynamically loaded elements
        setTimeout(hideElements, 50);
        setTimeout(hideElements, 100);
        setTimeout(hideElements, 200);
        setTimeout(hideElements, 500);
        setTimeout(hideElements, 1000);
        
        // Use MutationObserver to catch any elements added later
        if (window.MutationObserver) {
            const observer = new MutationObserver(function(mutations) {
                hideElements();
            });
            
            if (document.body) {
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
            }
        }
    }
})();

document.addEventListener('DOMContentLoaded', function() {
    // Check again on DOMContentLoaded
    if (window.location.pathname.includes('stripe_checkout') || 
        window.location.href.includes('stripe_checkout') ||
        document.querySelector('#payment-form') || 
        document.querySelector('#card-element')) {
        document.body.classList.add('stripe-checkout-page');
    }
    
    // Initialize all modules
    GarvalStore.init();
});

const GarvalStore = {
    // Configuration
    config: {
        currency: document.querySelector('meta[name="currency_symbol"]')?.content || '€',
        defaultLang: 'es',
        apiBase: '/api/method/garval_store.api'
    },

    // Initialize all modules
    init: function() {
        this.Header.init();
        this.MobileNav.init();
        this.LanguageSwitcher.init();
        this.Cart.init();
        this.Forms.init();
        this.ProductGrid.init();
        this.Quantity.init();
    },

    // ========================================
    // Header Module
    // ========================================
    Header: {
        header: null,
        scrollThreshold: 50,

        init: function() {
            this.header = document.getElementById('mainHeader');
            if (!this.header) return;

            this.bindEvents();
            this.checkScroll();
        },

        bindEvents: function() {
            window.addEventListener('scroll', this.checkScroll.bind(this));
        },

        checkScroll: function() {
            if (window.scrollY > this.scrollThreshold) {
                this.header.classList.add('scrolled');
            } else {
                this.header.classList.remove('scrolled');
            }
        }
    },

    // ========================================
    // Mobile Navigation Module
    // ========================================
    MobileNav: {
        toggle: null,
        overlay: null,
        closeBtn: null,

        init: function() {
            this.toggle = document.getElementById('mobileMenuToggle');
            this.overlay = document.getElementById('mobileNavOverlay');
            this.closeBtn = document.getElementById('mobileNavClose');

            if (!this.toggle || !this.overlay) return;

            this.bindEvents();
        },

        bindEvents: function() {
            this.toggle.addEventListener('click', this.openMenu.bind(this));
            if (this.closeBtn) {
                this.closeBtn.addEventListener('click', this.closeMenu.bind(this));
            }
            this.overlay.addEventListener('click', (e) => {
                if (e.target === this.overlay) {
                    this.closeMenu();
                }
            });

            // Close on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    this.closeMenu();
                }
            });
        },

        openMenu: function() {
            this.overlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        },

        closeMenu: function() {
            this.overlay.classList.remove('active');
            document.body.style.overflow = '';
        }
    },

    // ========================================
    // Language Switcher Module
    // ========================================
    LanguageSwitcher: {
        toggle: null,
        dropdown: null,

        init: function() {
            this.toggle = document.getElementById('langToggle');
            this.dropdown = document.getElementById('langDropdown');

            if (!this.toggle || !this.dropdown) return;

            this.bindEvents();
            this.loadSavedLanguage();
        },

        bindEvents: function() {
            this.toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                this.dropdown.classList.toggle('active');
            });

            // Close dropdown when clicking outside
            document.addEventListener('click', () => {
                this.dropdown.classList.remove('active');
            });

            // Language option click
            const langOptions = this.dropdown.querySelectorAll('.lang-option');
            langOptions.forEach(option => {
                option.addEventListener('click', (e) => {
                    e.preventDefault();
                    const url = new URL(option.href);
                    const lang = url.searchParams.get('lang');
                    this.setLanguage(lang);
                });
            });
        },

        loadSavedLanguage: function() {
            // Load saved language from cookie
            const savedLang = this.getCookie('lang');
            if (savedLang && !window.location.search.includes('lang=')) {
                const currentLang = document.documentElement.lang;
                if (savedLang !== currentLang) {
                    this.setLanguage(savedLang);
                }
            }
        },

        setLanguage: function(lang) {
            // Save language choice to cookie (respects both ES and EN)
            this.setCookie('lang', lang, 365); // Save for 1 year
            
            // Update URL with language parameter
            const url = new URL(window.location.href);
            url.searchParams.set('lang', lang);
            window.location.href = url.toString();
        },

        getCookie: function(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        },

        setCookie: function(name, value, days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            const expires = `expires=${date.toUTCString()}`;
            document.cookie = `${name}=${value};${expires};path=/;SameSite=Lax`;
        }
    },

    // ========================================
    // Cart Module
    // ========================================
    Cart: {
        items: [],
        countElements: null,

        init: function() {
            this.countElements = document.querySelectorAll('.cart-count');
            this.loadCart();
            this.bindEvents();
        },

        bindEvents: function() {
            // Add to cart buttons
            document.querySelectorAll('[data-add-to-cart]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const productId = btn.dataset.addToCart;
                    const productName = btn.dataset.productName;
                    const productPrice = parseFloat(btn.dataset.productPrice);
                    const productImage = btn.dataset.productImage;

                    this.addItem({
                        id: productId,
                        name: productName,
                        price: productPrice,
                        image: productImage,
                        quantity: 1
                    });
                });
            });

            // Remove from cart buttons
            document.querySelectorAll('[data-remove-from-cart]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const productId = btn.dataset.removeFromCart;
                    this.removeItem(productId);
                });
            });
        },

        loadCart: function() {
            const saved = localStorage.getItem('garval_cart');
            if (saved) {
                try {
                    this.items = JSON.parse(saved);
                    // Fix image paths in loaded items - convert to absolute URLs
                    this.items.forEach(item => {
                        if (item.image) {
                            if (!item.image.startsWith('http')) {
                                // Ensure it starts with /
                                const imagePath = item.image.startsWith('/') ? item.image : '/' + item.image;
                                // Convert to full absolute URL
                                item.image = window.location.origin + imagePath;
                            }
                        }
                    });
                } catch (e) {
                    this.items = [];
                }
            }
            this.updateCount();
        },

        saveCart: function() {
            localStorage.setItem('garval_cart', JSON.stringify(this.items));
            this.updateCount();
        },

        addItem: function(product) {
            const existing = this.items.find(item => item.id === product.id);
            if (existing) {
                existing.quantity += product.quantity;
            } else {
                // Ensure image has full absolute URL for PDF generation
                if (product.image) {
                    if (!product.image.startsWith('http')) {
                        // Ensure it starts with /
                        const imagePath = product.image.startsWith('/') ? product.image : '/' + product.image;
                        // Convert to full absolute URL
                        product.image = window.location.origin + imagePath;
                    }
                }
                this.items.push(product);
            }
            this.saveCart();
            this.showNotification('Producto añadido al carrito');
        },

        removeItem: function(productId) {
            this.items = this.items.filter(item => item.id !== productId);
            this.saveCart();
            this.refreshCartPage();
        },

        updateQuantity: function(productId, quantity) {
            const item = this.items.find(item => item.id === productId);
            if (item) {
                item.quantity = Math.max(1, quantity);
                this.saveCart();
            }
        },

        getTotal: function() {
            return this.items.reduce((total, item) => {
                return total + (item.price * item.quantity);
            }, 0);
        },

        getCount: function() {
            return this.items.reduce((count, item) => count + item.quantity, 0);
        },

        updateCount: function() {
            const count = this.getCount();
            this.countElements.forEach(el => {
                el.textContent = count;
            });
        },

        clear: function() {
            this.items = [];
            this.saveCart();
        },

        refreshCartPage: function() {
            if (window.location.pathname.includes('/cart')) {
                window.location.reload();
            }
        },

        showNotification: function(message) {
            const notification = document.createElement('div');
            notification.className = 'cart-notification';
            notification.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <span>${message}</span>
            `;
            notification.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #33652B;
                color: white;
                padding: 15px 25px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                z-index: 9999;
                animation: slideIn 0.3s ease;
            `;

            document.body.appendChild(notification);

            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    },

    // ========================================
    // Forms Module
    // ========================================
    Forms: {
        init: function() {
            this.setupContactForm();
            this.setupAuthForms();
            this.setupCheckoutForm();
        },

        setupContactForm: function() {
            const form = document.getElementById('contactForm');
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const submitBtn = form.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                
                // Get current language for messages
                const lang = GarvalStore.LanguageSwitcher.getCookie('lang') || 
                            document.documentElement.lang || 
                            new URLSearchParams(window.location.search).get('lang') || 
                            'es';
                const sendingText = lang === 'es' ? 'Enviando...' : 'Sending...';
                const successText = lang === 'es' 
                    ? 'Mensaje enviado correctamente. Nos pondremos en contacto pronto.' 
                    : 'Message sent successfully. We will contact you soon.';
                const errorText = lang === 'es' 
                    ? 'Error al enviar el mensaje. Por favor, inténtelo de nuevo.' 
                    : 'Error sending message. Please try again.';
                
                submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${sendingText}`;
                submitBtn.disabled = true;

                const formData = new FormData(form);
                
                // Get CSRF token from form
                const csrfToken = formData.get('csrf_token') || 
                                 document.querySelector('meta[name="csrf-token"]')?.content || 
                                 (window.frappe && window.frappe.csrf_token) || '';
                
                const data = {
                    full_name: formData.get('full_name'),
                    email: formData.get('email'),
                    phone: formData.get('phone') || null,
                    subject: formData.get('subject'),
                    message: formData.get('message')
                };

                try {
                    const response = await fetch(`${GarvalStore.config.apiBase}.contact.submit`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Frappe-CSRF-Token': csrfToken
                        },
                        body: JSON.stringify(data)
                    });

                    // Check if response is OK
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        console.error('Contact form API error:', response.status, errorData);
                        throw new Error(errorData.exc || errorData.message?.error || `HTTP ${response.status}: ${response.statusText}`);
                    }

                    const result = await response.json();

                    if (result.message && result.message.success) {
                        GarvalStore.Forms.showMessage(form, 'success', successText);
                        form.reset();
                    } else {
                        const errorMsg = result.message?.error || result.exc || result.error || errorText;
                        console.error('Contact form error:', result);
                        throw new Error(errorMsg);
                    }
                } catch (error) {
                    console.error('Contact form submission error:', error);
                    const errorMsg = error.message || errorText;
                    GarvalStore.Forms.showMessage(form, 'error', errorMsg);
                } finally {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }
            });
        },

        setupAuthForms: function() {
            // Auth forms are now handled by their respective page scripts
            // (customer_login.html and customer_signup.html)
            // This function is kept for backwards compatibility but does nothing
        },

        setupCheckoutForm: function() {
            const form = document.getElementById('checkoutForm');
            if (!form) return;

            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData(form);
                const cart = GarvalStore.Cart.items;

                if (cart.length === 0) {
                    GarvalStore.Forms.showMessage(form, 'error',
                        'El carrito está vacío');
                    return;
                }

                try {
                    const response = await fetch('/api/method/garval_store.api.checkout.create_order', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Frappe-CSRF-Token': frappe?.csrf_token || ''
                        },
                        body: JSON.stringify({
                            customer_info: Object.fromEntries(formData),
                            items: cart,
                            total: GarvalStore.Cart.getTotal()
                        })
                    });

                    const result = await response.json();

                    if (result.message && result.message.success) {
                        GarvalStore.Cart.clear();
                        window.location.href = `/order-confirmation?order=${result.message.order_id}`;
                    } else {
                        GarvalStore.Forms.showMessage(form, 'error',
                            result.message?.error || 'Error al procesar el pedido');
                    }
                } catch (error) {
                    GarvalStore.Forms.showMessage(form, 'error',
                        'Error al procesar el pedido');
                }
            });
        },

        showMessage: function(form, type, message) {
            // Remove existing message
            const existing = form.querySelector('.form-message');
            if (existing) existing.remove();

            const messageEl = document.createElement('div');
            messageEl.className = `form-message alert alert-${type}`;
            messageEl.innerHTML = `
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
                <span>${message}</span>
            `;

            form.insertBefore(messageEl, form.firstChild);

            // Auto-remove after 5 seconds
            setTimeout(() => messageEl.remove(), 5000);
        }
    },

    // ========================================
    // Product Grid Module
    // ========================================
    ProductGrid: {
        init: function() {
            this.setupFilters();
            this.setupSorting();
        },

        setupFilters: function() {
            const priceMin = document.getElementById('priceMin');
            const priceMax = document.getElementById('priceMax');
            const filterBtn = document.getElementById('applyFilters');

            if (filterBtn) {
                filterBtn.addEventListener('click', () => {
                    const params = new URLSearchParams(window.location.search);
                    if (priceMin?.value) params.set('price_min', priceMin.value);
                    if (priceMax?.value) params.set('price_max', priceMax.value);
                    window.location.search = params.toString();
                });
            }
        },

        setupSorting: function() {
            const sortSelect = document.getElementById('sortProducts');
            if (sortSelect) {
                sortSelect.addEventListener('change', () => {
                    const params = new URLSearchParams(window.location.search);
                    params.set('sort', sortSelect.value);
                    window.location.search = params.toString();
                });
            }
        }
    },

    // ========================================
    // Quantity Module
    // ========================================
    Quantity: {
        init: function() {
            document.querySelectorAll('.quantity-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const wrapper = btn.closest('.cart-quantity');
                    const input = wrapper.querySelector('.quantity-input');
                    const productId = input.dataset.productId;
                    let value = parseInt(input.value) || 1;

                    if (btn.classList.contains('quantity-minus')) {
                        value = Math.max(1, value - 1);
                    } else if (btn.classList.contains('quantity-plus')) {
                        value = value + 1;
                    }

                    input.value = value;

                    if (productId) {
                        GarvalStore.Cart.updateQuantity(productId, value);
                        this.updateRowTotal(wrapper, value);
                    }
                });
            });

            // Direct input change
            document.querySelectorAll('.quantity-input').forEach(input => {
                input.addEventListener('change', () => {
                    const productId = input.dataset.productId;
                    const value = Math.max(1, parseInt(input.value) || 1);
                    input.value = value;

                    if (productId) {
                        GarvalStore.Cart.updateQuantity(productId, value);
                        const wrapper = input.closest('.cart-quantity');
                        this.updateRowTotal(wrapper, value);
                    }
                });
            });
        },

        updateRowTotal: function(wrapper, quantity) {
            const row = wrapper.closest('tr');
            if (!row) return;

            const priceCell = row.querySelector('.cart-price');
            const totalCell = row.querySelector('.cart-total');

            if (priceCell && totalCell) {
                const price = parseFloat(priceCell.dataset.price);
                totalCell.textContent = `${GarvalStore.config.currency}${(price * quantity).toFixed(2)}`;
            }

            // Update cart totals
            this.updateCartTotals();
        },

        updateCartTotals: function() {
            const subtotalEl = document.getElementById('cartSubtotal');
            const totalEl = document.getElementById('cartTotal');

            if (subtotalEl && totalEl) {
                const total = GarvalStore.Cart.getTotal();
                subtotalEl.textContent = `${GarvalStore.config.currency}${total.toFixed(2)}`;
                totalEl.textContent = `${GarvalStore.config.currency}${total.toFixed(2)}`;
            }
        }
    },

    // ========================================
    // Utility Functions
    // ========================================
    Utils: {
        formatCurrency: function(amount) {
            return `${GarvalStore.config.currency}${parseFloat(amount).toFixed(2)}`;
        },

        debounce: function(func, wait) {
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
    }
};

// Add CSS animations
const garvalAnimationStyle = document.createElement('style');
garvalAnimationStyle.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(garvalAnimationStyle);

// Expose GarvalStore to global scope for use in HTML templates
window.GarvalStore = GarvalStore;

})();
