app_name = "garval_store"
app_title = "Garval Store"
app_publisher = "Kashif Ali"
app_description = "E-commerce platform with bilingual support (Spanish/English)"
app_email = "kashif@example.com"
app_license = "MIT"

# Fixtures - Custom Fields and Client Scripts
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["name", "in", ["User-email_verified", "User-email_verification_key"]]]
    },
    {
        "dt": "Client Script",
        "filters": [["name", "=", "Payment Request - Order Confirmation Button"]]
    }
]

# Website
website_route_rules = [
    {"from_route": "/home", "to_route": "home"},
    {"from_route": "/about", "to_route": "about"},
    {"from_route": "/contact", "to_route": "contact"},
    {"from_route": "/shop", "to_route": "shop"},
    {"from_route": "/product/<name>", "to_route": "product"},
    {"from_route": "/cart", "to_route": "cart"},
    {"from_route": "/checkout", "to_route": "checkout"},
    {"from_route": "/order_confirmation", "to_route": "order_confirmation"},
    {"from_route": "/my-account", "to_route": "my_account"},
    {"from_route": "/customer-login", "to_route": "customer_login"},
    {"from_route": "/customer-signup", "to_route": "customer_signup"},
    {"from_route": "/verify-email", "to_route": "verify_email"},
    {"from_route": "/payment", "to_route": "payment"},
    {"from_route": "/payment-success", "to_route": "payment_success"},
    {"from_route": "/payment-failed", "to_route": "payment_failed"},
    {"from_route": "/politica-privacidad", "to_route": "politica_privacidad"},
    {"from_route": "/aviso-legal", "to_route": "aviso_legal"},
    {"from_route": "/politica-cookies", "to_route": "politica_cookies"},
    {"from_route": "/declaracion-accesibilidad", "to_route": "declaracion_accesibilidad"},
]

# Home page
home_page = "home"

# App includes (for desk/backend - these will NOT affect /login)
app_include_css = []

app_include_js = []

# Web includes (for website pages only)
web_include_css = [
    "/assets/garval_store/css/garval.css"
]

web_include_js = [
    "/assets/garval_store/js/garval.js"
]

# DocTypes
# doc_events = {}

# On login hook - create Customer if not exists (for SSO users)
on_login = "garval_store.user_hooks.on_user_login"

# On session creation hook - run cart setup as Administrator to avoid permission errors
on_session_creation = "garval_store.user_hooks.on_session_creation"

# Scheduled Tasks
# scheduler_events = {}

# Installation hooks
after_install = "garval_store.install.after_install"

# Website context
website_context = {
    "favicon": "/assets/garval_store/images/favicon.ico",
    "splash_image": "/assets/garval_store/images/logo.png"
}

# Update website context to conditionally exclude CSS from Frappe login/signup pages
update_website_context = "garval_store.utils.update_website_context"

# Jinja environment customizations
jinja = {
    "methods": [
        "garval_store.utils.get_lang"
    ]
}

# Override whitelisted methods
override_whitelisted_methods = {}

# Override doctype classes
override_doctype_class = {
	"Customer": "garval_store.overrides.customer.Customer",
}

# Default language
default_language = "es"
