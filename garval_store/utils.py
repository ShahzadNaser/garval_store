import frappe
from frappe import _

def resolve_product_path(path):
    """Custom path resolver for /product/... routes"""
    # Only handle product routes - for others, call normal routing
    # When a path resolver exists, it overrides normal routing, so we need to
    # manually call resolve_path for non-product routes to ensure route rules work
    if path and path.startswith("product/"):
        # Extract the slug (everything after product/)
        slug = path.replace("product/", "", 1).split("?")[0].rstrip("/")
        # Set form_dict so product.py can access it
        if not hasattr(frappe.local, "form_dict"):
            frappe.local.form_dict = frappe._dict()
        frappe.local.form_dict["name"] = slug
        # Return the endpoint for our product page
        return "product"
    
    # For non-product routes, call normal Frappe routing
    # This ensures route rules (like /verify-email -> verify_email) work correctly
    from frappe.website.path_resolver import resolve_path
    try:
        return resolve_path(path)
    except Exception:
        # If resolve_path fails, return path as fallback
        return path

def update_website_context(context):
    """Update website context - used to exclude CSS from Frappe default pages"""
    # Get the current path
    path = frappe.request.path if frappe.request else ""
    
    # Check if we're on stripe_checkout page
    is_stripe_checkout = (
        'stripe_checkout' in path or
        context.get('path') == 'stripe_checkout' or
        context.get('pathname') == 'stripe_checkout' or
        (hasattr(context, 'pathname') and 'stripe_checkout' in str(context.get('pathname', '')))
    )
    
    # Add inline style to hide navbar and page-header-wrapper on stripe_checkout page
    if is_stripe_checkout:
        if 'head_include' not in context:
            context['head_include'] = ''
        context['head_include'] += '''
<style>
body[data-path="stripe_checkout"] .navbar,
body[data-path="stripe_checkout"] nav.navbar,
body[data-path="stripe_checkout"] nav,
body[data-path="stripe_checkout"] .page-header-wrapper,
body[data-path="stripe_checkout"] .page-breadcrumbs {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 0 !important;
}
</style>
<script>
(function() {
    if (document.body && document.body.getAttribute('data-path') === 'stripe_checkout') {
        var style = document.createElement('style');
        style.textContent = 'body[data-path="stripe_checkout"] .navbar, body[data-path="stripe_checkout"] nav.navbar, body[data-path="stripe_checkout"] nav, body[data-path="stripe_checkout"] .page-header-wrapper, body[data-path="stripe_checkout"] .page-breadcrumbs { display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important; opacity: 0 !important; }';
        document.head.appendChild(style);
        
        function hideElements() {
            var navbars = document.querySelectorAll('.navbar, nav.navbar, nav');
            var wrappers = document.querySelectorAll('.page-header-wrapper');
            var breadcrumbs = document.querySelectorAll('.page-breadcrumbs');
            
            [].forEach.call(navbars, function(el) { el.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important; opacity: 0 !important;'; });
            [].forEach.call(wrappers, function(el) { el.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; margin: 0 !important; padding: 0 !important; opacity: 0 !important;'; });
            [].forEach.call(breadcrumbs, function(el) { el.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important;'; });
        }
        
        if (document.body) hideElements();
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', hideElements);
        } else {
            hideElements();
        }
        setTimeout(hideElements, 50);
        setTimeout(hideElements, 100);
        setTimeout(hideElements, 500);
    }
})();
</script>
'''
    
    # List of Frappe default pages where we don't want our custom CSS
    frappe_pages = ['/login', '/signup', '/app', '/desk', '/api']

    # Check if current path is a Frappe default page
    is_frappe_page = any(path.startswith(page) for page in frappe_pages)

    # If it's a Frappe page, remove our custom CSS from web_include_css
    if is_frappe_page:
        context['web_include_css'] = []
        context['web_include_js'] = []
    
    # Add currency symbol to all pages
    context['currency_symbol'] = get_currency_symbol()

def get_lang():
    """Get current language from request or cookies. Defaults to ES (Spanish)."""
    lang = None

    # Try from URL parameter first
    if frappe.request and frappe.request.args:
        lang = frappe.request.args.get('lang')

    # Try from cookie (respects user's saved choice - ES or EN)
    if not lang:
        try:
            lang = frappe.request.cookies.get('lang') if frappe.request else None
        except:
            pass

    # Default to Spanish (ES) if no valid language found
    if not lang or lang not in ['es', 'en']:
        lang = 'es'

    return lang

def set_lang():
    """Set the language for the current request context.
    This must be called before rendering templates to enable translations.
    """
    lang = get_lang()
    frappe.local.lang = lang
    return lang


def require_email_verification():
    """Check if user's email is verified. Redirect to login/verify if not.
    Returns True if verified, False otherwise (and redirects)"""
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/customer-login"
        raise frappe.Redirect
    
    # Skip check for Administrator
    if frappe.session.user in ("Administrator",):
        return True
    
    # Check email verification (SSO users are auto-verified in on_user_login hook)
    email_verified = get_email_verified(frappe.session.user)
    if not email_verified:
        # Logout and show error message
        from frappe.auth import LoginManager
        login_manager = LoginManager()
        login_manager.logout()
        
        # Show error message that verification email was sent
        from frappe import _
        lang = frappe.local.lang or "es"
        if lang == "es":
            title = _("Verificación de Email Requerida")
            message = _("Por favor, verifica tu dirección de correo electrónico antes de continuar. Se ha enviado un correo de verificación a tu dirección de correo electrónico.")
            home_label = _("Ir a Inicio")
        else:
            title = _("Email Verification Required")
            message = _("Please verify your email address before continuing. A verification email has been sent to your email address.")
            home_label = _("Go to Home")
        
        frappe.redirect_to_message(
            title=title,
            html=f"<p>{message}</p>",
            indicator_color="orange",
            context={
                "primary_action": "/",
                "primary_label": home_label
            }
        )
        raise frappe.Redirect
    
    return True

def get_currency_symbol(company=None):
    """Get currency symbol for the given company or default company"""
    try:
        if not company:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            company = frappe.get_all("Company", limit=1)
            company = company[0].name if company else None
        
        if company:
            currency = frappe.db.get_value("Company", company, "default_currency", cache=True)
        else:
            currency = frappe.db.get_single_value("Global Defaults", "default_currency")
        
        if currency:
            symbol = frappe.db.get_value("Currency", currency, "symbol", cache=True)
            if symbol:
                return symbol
        
        # Fallback to currency code if symbol not found
        return currency or "€"
    except Exception:
        return "€"

def format_currency(amount, company=None):
    """Format amount with currency symbol"""
    symbol = get_currency_symbol(company)
    return f"{symbol}{float(amount):.2f}"

def get_featured_products(limit=4):
    """Get featured products using webshop's product query API"""
    try:
        from webshop.webshop.api import get_product_filter_data
        
        # Use webshop's API to get products sorted by ranking
        result = get_product_filter_data({
            "start": 0,
            "field_filters": {}
        })
        
        items = result.get("items", [])[:limit]
        
        # Format items to match expected structure
        products = []
        for item in items:
            # Check stock status - webshop returns in_stock as 0 or 1 (or False/True)
            in_stock = item.get("in_stock")
            if in_stock is None:
                # If not set, check if it's a stock item - if yes, assume out of stock if no stock_qty
                is_stock_item = item.get("is_stock_item", False)
                out_of_stock = bool(is_stock_item and item.get("stock_qty", 0) == 0)
            else:
                # in_stock is 0 (out) or 1 (in stock)
                out_of_stock = not bool(in_stock)
            
            product = frappe._dict({
                "item_code": item.get("item_code"),
                "name": item.get("web_item_name") or item.get("item_name"),
                "item_name": item.get("item_name"),
                "slug": item.get("route") or item.get("item_code"),
                "image": item.get("website_image") or item.get("image"),
                "description": item.get("short_description") or item.get("description"),
                "price": item.get("price_list_rate") or 0,
                "formatted_price": item.get("formatted_price") or "€0.00",
                "out_of_stock": out_of_stock
            })
            products.append(product)
        
        return products

    except Exception as e:
        frappe.log_error(f"Error fetching featured products: {str(e)}")
        return []

def get_all_products(filters=None, limit=20, offset=0, sort_by="modified", sort_order="desc"):
    """Get all products using webshop's product filter API"""
    try:
        from webshop.webshop.api import get_product_filter_data
        
        # Build field filters for webshop API
        field_filters = {}
        if filters:
            if filters.get('item_group'):
                field_filters['item_group'] = filters.get('item_group')
        
        # Map sort_by to webshop's expected format
        # webshop sorts by ranking by default, we'll handle custom sorting after
        query_args = {
            "start": offset,
            "field_filters": field_filters
        }
        
        # Add search if needed (for future use)
        if filters and filters.get('search'):
            query_args["search"] = filters.get('search')
        
        # Get products from webshop
        result = get_product_filter_data(query_args)
        items = result.get("items", [])
        
        # Format products to match expected structure
        products = []
        for item in items:
            # Apply price filters if specified
            price = item.get("price_list_rate") or 0
            if filters:
                price_min = filters.get('price_min')
                price_max = filters.get('price_max')
                if price_min and price < float(price_min):
                    continue
                if price_max and price > float(price_max):
                    continue
            
            product = frappe._dict({
                "item_code": item.get("item_code"),
                "name": item.get("web_item_name") or item.get("item_name"),
                "item_name": item.get("item_name"),
                "slug": item.get("route") or item.get("item_code"),
                "image": item.get("website_image") or item.get("image"),
                "description": item.get("short_description") or item.get("description"),
                "price": price,
                "formatted_price": item.get("formatted_price") or "€0.00",
                "out_of_stock": not item.get("in_stock", False) if item.get("is_stock_item") else False
            })
            products.append(product)
        
        # Apply custom sorting if needed
        if sort_by == "price":
            reverse = sort_order == "desc"
            products.sort(key=lambda x: x.get('price', 0), reverse=reverse)
        elif sort_by == "name" or sort_by == "item_name":
            reverse = sort_order == "desc"
            products.sort(key=lambda x: x.get('name', '').lower(), reverse=reverse)
        # Default sorting by ranking is already done by webshop
        
        # Limit results
        return products[:limit]

    except Exception as e:
        frappe.log_error(f"Error fetching products: {str(e)}")
        return []

def get_product_by_slug(slug):
    """Get single product by slug/route using webshop's product info API"""
    if not slug:
        return None
        
    slug = slug.strip()  # Remove any whitespace
        
    try:
        from webshop.webshop.shopping_cart.product_info import get_product_info_for_website
        
        # First try to find Website Item by route or item_code
        website_item_name = None
        item_code = None
        
        if frappe.db.exists("DocType", "Website Item"):
            # Try by full route first (may include item group path like "demo-item-group/website-product-1-f2rah")
            if slug:
                # First try exact route match
                website_item_name = frappe.db.get_value("Website Item", {"route": slug}, "name")
                if website_item_name:
                    item_code = frappe.db.get_value("Website Item", website_item_name, "item_code")
                else:
                    # Try with LIKE to match routes (handles trailing slashes or variations)
                    website_items = frappe.db.get_all(
                        "Website Item",
                        filters={"route": ["like", f"{slug}%"]},
                        fields=["name", "route"],
                        limit=1
                    )
                    if website_items:
                        website_item_name = website_items[0].name
                        item_code = frappe.db.get_value("Website Item", website_item_name, "item_code")
            
            # If not found by full route, try to find by the last part of the route (product name only)
            if not website_item_name and '/' in slug:
                # Extract just the product name part (after last slash)
                product_name = slug.split('/')[-1]
                website_item_name = frappe.db.get_value("Website Item", {"route": product_name}, "name")
                if not website_item_name:
                    # Try with LIKE to match routes ending with the product name
                    website_items = frappe.db.get_all(
                        "Website Item",
                        filters={"route": ["like", f"%/{product_name}"]},
                        fields=["name", "route"],
                        limit=1
                    )
                    if website_items:
                        website_item_name = website_items[0].name
                
                if website_item_name:
                    item_code = frappe.db.get_value("Website Item", website_item_name, "item_code")
            
            # Fallback: try by item_code (slug might be item_code)
            if not item_code:
                # Try exact item_code match
                website_item_name = frappe.db.get_value("Website Item", {"item_code": slug}, "name")
                if website_item_name:
                    item_code = slug
                else:
                    # Try if slug is the Website Item name itself
                    if frappe.db.exists("Website Item", slug):
                        website_item_name = slug
                        item_code = frappe.db.get_value("Website Item", slug, "item_code")
        
        # If still not found, try Item directly
        if not item_code:
            if frappe.db.exists("Item", slug):
                item_code = slug
            else:
                return None
        
        # Get product info using webshop's API
        product_info_data = get_product_info_for_website(item_code, skip_quotation_creation=True)
        product_info = product_info_data.get("product_info", {})
        cart_settings = product_info_data.get("cart_settings", {})
        
        # Get Website Item document for additional details
        if website_item_name:
            website_item = frappe.get_doc("Website Item", website_item_name)
        else:
            # Try to get Website Item by item_code
            website_item_name = frappe.db.get_value("Website Item", {"item_code": item_code}, "name")
            if website_item_name:
                website_item = frappe.get_doc("Website Item", website_item_name)
            else:
                # Fallback to Item
                item = frappe.get_doc("Item", item_code)
                return {
                    "item_code": item_code,
                    "name": item.item_name,
                    "description": item.description,
                    "short_description": item.description,
                    "image": item.image,
                    "images": get_product_images(item.name, "Item"),
                    "price": product_info.get("price", {}).get("price") or 0,
                    "formatted_price": product_info.get("price", {}).get("formatted_price") or "€0.00",
                    "out_of_stock": not product_info.get("in_stock", False),
                    "uom": product_info.get("uom") or item.stock_uom
                }
        
        # Get price info
        price_info = product_info.get("price", {})
        
        return {
            "item_code": item_code,
            "name": website_item.web_item_name or website_item.item_name,
            "description": website_item.web_long_description or website_item.short_description,
            "short_description": website_item.short_description,
            "image": website_item.website_image or frappe.db.get_value("Item", item_code, "image"),
            "images": get_product_images(website_item.name, "Website Item"),
            "price": price_info.get("price_list_rate") or 0,
            "formatted_price": price_info.get("formatted_price") or "€0.00",
            "out_of_stock": not product_info.get("in_stock", False) if product_info.get("is_stock_item") else False,
            "uom": product_info.get("uom") or website_item.stock_uom,
            "stock_qty": product_info.get("stock_qty", 0),
            "on_backorder": product_info.get("on_backorder", False)
        }
            
    except Exception as e:
        frappe.log_error(f"Error fetching product '{slug}': {str(e)}", "get_product_by_slug")
        import traceback
        frappe.log_error(traceback.format_exc(), "get_product_by_slug_traceback")

    return None

def send_bank_transfer_invoice_email(sales_invoice, sales_order, customer_email, customer_name, company, payment_request=None, payment_gateway_account=None):
    """
    Send invoice email with bank details for Bank Transfer payment using Payment Gateway Account message template
    """
    try:
        # Payment Gateway Account must be provided (already selected on checkout)
        if not payment_gateway_account:
            frappe.throw(_("Payment Gateway Account is required for sending bank transfer email"))
        
        # Get bank account details
        bank_account = None
        if payment_request and payment_request.bank_account:
            bank_account = payment_request.bank_account
        else:
            bank_account = frappe.db.get_value(
                "Bank Account",
                {"company": company, "is_company_account": 1, "is_default": 1, "disabled": 0},
                "name"
            )
            if not bank_account:
                bank_account = frappe.db.get_value(
                    "Bank Account",
                    {"company": company, "is_company_account": 1, "disabled": 0},
                    "name",
                    order_by="creation desc"
                )
        
        if not bank_account:
            error_msg = _("No bank account found for company {0}. Please configure a bank account for Bank Transfer payments.").format(company)
            frappe.log_error(error_msg, "Bank Transfer Email Error")
            frappe.throw(error_msg)
        
        # Get bank details
        bank_details = frappe.db.get_value(
            "Bank Account",
            bank_account,
            ["iban", "swift_number", "bank_account_no", "bank", "branch_code"],
            as_dict=True
        )
        
        # Get SWIFT from Bank doctype if available
        if bank_details and bank_details.get("bank"):
            swift = frappe.db.get_value("Bank", bank_details.bank, "swift_number")
            if swift:
                bank_details["swift_number"] = swift
        
        # Generate invoice PDF
        invoice_pdf = frappe.attach_print(
            "Sales Invoice",
            sales_invoice.name,
            print_format="Standard"
        )
        
        # Get email template from Payment Gateway Account message field
        email_template_content = payment_gateway_account.message or ""
        
        # Render template with sales_invoice as doc (template uses {{ doc.company }}, {{ doc.name }}, etc.)
        rendered_content = frappe.render_template(
            email_template_content,
            {"doc": sales_invoice}
        )
        
        # Email subject
        subject = getattr(payment_gateway_account, "subject", None) or _("Invoice pending for {0}").format(sales_order)
        
        # Send email with rendered content
        frappe.sendmail(
            recipients=[customer_email],
            subject=subject,
            content=rendered_content,
            attachments=[invoice_pdf],
            reference_doctype="Sales Invoice",
            reference_name=sales_invoice.name,
            now=True
        )
        
        frappe.log_error(f"Bank transfer invoice email sent to {customer_email} for invoice {sales_invoice.name}", "Bank Transfer Email")
        return True
        
    except Exception as e:
        error_msg = f"Error sending bank transfer email: {str(e)}\nTraceback: {frappe.get_traceback()}"
        frappe.log_error(error_msg, "Bank Transfer Email Error")
        # Re-raise the exception so order creation fails
        raise

def get_product_images(doc_name, doctype="Website Item"):
    """Get all images for a product"""
    images = []
    try:
        if doctype == "Website Item":
            slideshow = frappe.db.get_value("Website Item", doc_name, "slideshow")
            if slideshow:
                images = frappe.get_all(
                    "Website Slideshow Item",
                    filters={"parent": slideshow},
                    fields=["image"],
                    order_by="idx"
                )
                images = [img.image for img in images]
    except:
        pass
    return images

def get_item_price(item_code, price_list=None):
    """Get item price from ERPNext Price List"""
    try:
        if not price_list:
            price_list = frappe.db.get_single_value("Webshop Settings", "price_list")

        if not price_list:
            price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")

        price = frappe.db.get_value(
            "Item Price",
            {"item_code": item_code, "price_list": price_list, "selling": 1},
            "price_list_rate"
        )

        if price:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
            return {
                "price": float(price),
                "formatted_price": format_currency(price, company)
            }
    except Exception as e:
        frappe.log_error(f"Error getting price for {item_code}: {str(e)}")

    company = frappe.db.get_single_value("Global Defaults", "default_company")
    return {"price": 0, "formatted_price": format_currency(0, company)}

def has_stock(item_code, warehouse=None):
    """Check if item has stock"""
    try:
        from erpnext.stock.utils import get_stock_balance

        if not warehouse:
            warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")

        if warehouse:
            qty = get_stock_balance(item_code, warehouse)
            return qty > 0
    except:
        pass

    return True  # Default to available if can't check

def get_item_groups():
    """Get item groups for filtering"""
    try:
        groups = frappe.get_all(
            "Item Group",
            filters={"show_in_website": 1, "is_group": 0},
            fields=["name", "item_group_name"],
            order_by="name"
        )
        return groups
    except:
        return []

def get_customer_from_user(user=None):
    """Get ERPNext Customer linked to user"""
    if not user:
        user = frappe.session.user

    if user == "Guest":
        return None

    customer = frappe.db.get_value("Customer", {"email_id": user}, "name")
    if not customer:
        # Check contact
        contact = frappe.db.get_value("Contact", {"user": user}, "name")
        if contact:
            links = frappe.get_all(
                "Dynamic Link",
                filters={"parent": contact, "link_doctype": "Customer"},
                fields=["link_name"]
            )
            if links:
                customer = links[0].link_name

    return customer


def get_or_create_email_verification(user):
    """Get or create User Email Verification record for a user"""
    if not user or user == "Guest":
        return None
    
    # Check if record exists
    verification = frappe.db.get_value("User Email Verification", {"user": user}, "name")
    
    if verification:
        return verification
    
    # Create new record
    try:
        doc = frappe.get_doc({
            "doctype": "User Email Verification",
            "user": user,
            "email_verified": 0
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception as e:
        frappe.log_error(f"Error creating email verification record for {user}: {str(e)}")
        return None


def get_email_verified(user):
    """Get email verified status for a user"""
    if not user or user == "Guest":
        return False
    
    verification_name = get_or_create_email_verification(user)
    if not verification_name:
        return False
    
    return bool(frappe.db.get_value("User Email Verification", verification_name, "email_verified"))


def set_email_verified(user, verified):
    """Set email verified status for a user"""
    if not user or user == "Guest":
        return False
    
    verification_name = get_or_create_email_verification(user)
    if not verification_name:
        return False
    
    frappe.db.set_value("User Email Verification", verification_name, "email_verified", 1 if verified else 0)
    frappe.db.commit()
    return True


def get_email_verification_key(user):
    """Get email verification key for a user"""
    if not user or user == "Guest":
        return None
    
    verification_name = get_or_create_email_verification(user)
    if not verification_name:
        return None
    
    return frappe.db.get_value("User Email Verification", verification_name, "email_verification_key")


def set_email_verification_key(user, key):
    """Set email verification key for a user"""
    if not user or user == "Guest":
        return False
    
    verification_name = get_or_create_email_verification(user)
    if not verification_name:
        return False
    
    frappe.db.set_value("User Email Verification", verification_name, "email_verification_key", key)
    frappe.db.commit()
    return True


def get_last_verification_email_sent(user):
    """Get last verification email sent timestamp for a user"""
    if not user or user == "Guest":
        return None
    
    verification_name = get_or_create_email_verification(user)
    if not verification_name:
        return None
    
    return frappe.db.get_value("User Email Verification", verification_name, "last_verification_email_sent")


def set_last_verification_email_sent(user, timestamp):
    """Set last verification email sent timestamp for a user"""
    if not user or user == "Guest":
        return False
    
    verification_name = get_or_create_email_verification(user)
    if not verification_name:
        return False
    
    frappe.db.set_value("User Email Verification", verification_name, "last_verification_email_sent", timestamp)
    frappe.db.commit()
    return True

def get_customer_orders(customer, limit=10):
    """Get customer's sales orders - exclude cancelled orders"""
    if not customer:
        return []

    try:
        orders = frappe.get_all(
            "Sales Order",
            filters={
                "customer": customer, 
                "docstatus": ["!=", 2],  # Exclude cancelled (docstatus 2)
                "status": ["!=", "Cancelled"]  # Also exclude by status
            },
            fields=[
                "name", "transaction_date", "grand_total",
                "status", "delivery_status", "billing_status"
            ],
            order_by="creation desc",
            limit=limit
        )
        return orders
    except:
        return []

def create_customer_from_signup(data):
    """Create ERPNext Customer from signup data"""
    try:
        # Create User
        if frappe.db.exists("User", data.get("email")):
            return {"success": False, "error": _("Email already registered")}

        user = frappe.get_doc({
            "doctype": "User",
            "email": data.get("email"),
            "first_name": data.get("full_name", "").split()[0],
            "last_name": " ".join(data.get("full_name", "").split()[1:]) or "",
            "enabled": 1,
            "new_password": data.get("password"),
            "send_welcome_email": 0,
            "user_type": "Website User"
        })
        user.insert(ignore_permissions=True)

        # Add Customer role to user
        user.add_roles("Customer")

        # Check if Customer already exists with this email (to prevent duplicates)
        existing_customer = frappe.db.get_value("Customer", {"email_id": data.get("email")}, "name")
        if existing_customer:
            # Customer exists but User doesn't - this is the bug scenario
            # Link the existing customer to the new user
            frappe.log_error(
                f"Customer {existing_customer} already exists for email {data.get('email')} but User doesn't. "
                f"Creating User and linking to existing Customer.",
                "Customer Signup - Existing Customer"
            )
            customer_name = existing_customer
            # Update customer name if needed
            frappe.db.set_value("Customer", existing_customer, "customer_name", data.get("full_name"))
        else:
            # Create Customer
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": data.get("full_name"),
                "customer_type": "Individual",
                "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual",
                "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
                "email_id": data.get("email")
            })
            customer.insert(ignore_permissions=True)
            customer_name = customer.name

        # Create Contact and Link
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": data.get("full_name", "").split()[0],
            "last_name": " ".join(data.get("full_name", "").split()[1:]) or "",
            "user": user.name,
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer.name
            }]
        })
        contact.append("email_ids", {
            "email_id": data.get("email"),
            "is_primary": 1
        })
        if data.get("phone"):
            contact.append("phone_nos", {
                "phone": data.get("phone"),
                "is_primary_phone": 1
            })
        contact.insert(ignore_permissions=True)

        frappe.db.commit()

        return {"success": True, "customer": customer.name, "user": user.name}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error creating customer: {str(e)}")
        return {"success": False, "error": str(e)}

def get_payment_gateways():
    """Get all enabled payment gateway accounts"""
    try:
        gateways = frappe.get_all(
            "Payment Gateway Account",
            fields=["name", "payment_gateway", "payment_account", "currency"]
        )

        payment_options = []
        for gateway in gateways:
            payment_options.append({
                "name": gateway.name,
                "gateway": gateway.payment_gateway,
                "label": gateway.payment_gateway,
                "currency": gateway.currency
            })

        return payment_options
    except Exception as e:
        frappe.log_error(f"Error fetching payment gateways: {str(e)}")
        return []

def create_sales_order_from_cart(cart_data, customer_info):
    """Create ERPNext Sales Order from cart"""
    try:
        customer = get_customer_from_user()

        if not customer:
            return {
                "success": False,
                "error": _("Please login to place an order")
            }

        # Check if user's email is verified
        email_verified = get_email_verified(frappe.session.user)
        if not email_verified:
            return {
                "success": False,
                "error": _("Please verify your email before placing an order. Check your inbox for the verification link."),
                "email_not_verified": True
            }

        # Get company
        company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            company = frappe.get_all("Company", limit=1)[0].name

        # Validate and process cart items BEFORE creating Sales Order
        from frappe.utils import flt
        validated_items = []
        validation_errors = []

        # Get default warehouse for stock check
        default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")

        # Maximum quantity per item (prevent unrealistic orders)
        MAX_QUANTITY_PER_ITEM = 100

        for item in cart_data.get("items", []):
            item_code = item.get("id") or item.get("item_code")
            if not item_code:
                continue

            # 1. Validate item exists and is enabled
            item_data = frappe.db.get_value(
                "Item",
                item_code,
                ["name", "item_name", "disabled", "is_sales_item", "has_variants"],
                as_dict=True
            )

            if not item_data:
                validation_errors.append(_("Item {0} not found").format(item_code))
                continue

            if item_data.disabled:
                validation_errors.append(_("Item {0} is not available").format(item_data.item_name))
                continue

            if not item_data.is_sales_item:
                validation_errors.append(_("Item {0} is not for sale").format(item_data.item_name))
                continue

            if item_data.has_variants:
                validation_errors.append(_("Please select a variant for {0}").format(item_data.item_name))
                continue

            # 2. Check if item is published on website (Website Item or show_in_website)
            is_published = frappe.db.exists("Website Item", {"item_code": item_code, "published": 1})
            if not is_published:
                is_published = frappe.db.get_value("Item", item_code, "show_in_website")

            if not is_published:
                validation_errors.append(_("Item {0} is not available for online purchase").format(item_data.item_name))
                continue

            # 3. Validate quantity
            qty = flt(item.get("quantity", 1))
            if qty <= 0:
                validation_errors.append(_("Invalid quantity for {0}").format(item_data.item_name))
                continue

            if qty > MAX_QUANTITY_PER_ITEM:
                validation_errors.append(_("Maximum quantity for {0} is {1}").format(item_data.item_name, MAX_QUANTITY_PER_ITEM))
                continue

            # 4. Check stock availability
            if default_warehouse:
                try:
                    from erpnext.stock.utils import get_stock_balance
                    available_stock = get_stock_balance(item_code, default_warehouse)
                    if available_stock < qty:
                        if available_stock <= 0:
                            validation_errors.append(_("Item {0} is out of stock").format(item_data.item_name))
                        else:
                            validation_errors.append(_("Only {0} units of {1} available").format(int(available_stock), item_data.item_name))
                        continue
                except Exception:
                    pass  # Continue if stock check fails (item might not be stock tracked)

            # 5. Get price from server (NEVER trust client price)
            server_price = get_item_price(item_code)
            rate = server_price.get("price", 0)

            if rate <= 0:
                validation_errors.append(_("Price not available for {0}").format(item_data.item_name))
                continue

            validated_items.append({
                "item_code": item_code,
                "qty": qty,
                "rate": rate
            })

        # Check if we have any valid items
        if not validated_items:
            error_msg = _("No valid items in cart")
            if validation_errors:
                error_msg = ". ".join(validation_errors)
            return {
                "success": False,
                "error": error_msg
            }

        # If there were some validation errors but also valid items, log them
        if validation_errors:
            frappe.log_error(
                f"Cart validation warnings for customer {customer}: {validation_errors}",
                "Cart Validation Warning"
            )

        # Create Sales Order with validated items
        so = frappe.get_doc({
            "doctype": "Sales Order",
            "customer": customer,
            "company": company,
            "delivery_date": frappe.utils.add_days(frappe.utils.nowdate(), 7),
            "order_type": "Shopping Cart",
            "contact_email": customer_info.get("email"),
            "contact_mobile": customer_info.get("phone"),
            "items": []
        })

        # Add validated items to Sales Order
        for item in validated_items:
            so.append("items", item)

        # Add shipping address if provided
        if customer_info.get("selected_address"):
            so.shipping_address_name = customer_info.get("selected_address")
        
        tax_template_name = frappe.db.get_value(
            "Sales Taxes and Charges Template",
            {
                "company": company,
                "disabled": 0
            },
            "name",
            order_by="is_default desc, creation desc"
        )
        
        if tax_template_name:
            so.taxes_and_charges = tax_template_name
            # Get taxes from template and append to Sales Order
            from erpnext.controllers.accounts_controller import get_taxes_and_charges
            taxes_list = get_taxes_and_charges("Sales Taxes and Charges Template", tax_template_name)
            if taxes_list:
                so.set("taxes", [])
                for tax_row in taxes_list:
                    so.append("taxes", tax_row)
        
        so.calculate_taxes_and_totals()

        so.insert(ignore_permissions=True)

        frappe.db.commit()

        return {
            "success": True,
            "order_id": so.name,
            "order": so.as_dict()
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Error creating sales order: {str(e)}")
        return {"success": False, "error": str(e)}

def calculate_taxes_and_charges(subtotal, company=None):
    """Calculate taxes and charges for a given subtotal based on enabled tax template"""
    try:
        if not company:
            company = frappe.db.get_single_value("Global Defaults", "default_company")
            if not company:
                company = frappe.get_all("Company", limit=1)[0].name

        # Get enabled tax template for company
        tax_template_name = frappe.db.get_value(
            "Sales Taxes and Charges Template",
            {
                "company": company,
                "disabled": 0
            },
            "name",
            order_by="is_default desc, creation desc"
        )

        if not tax_template_name:
            return {
                "subtotal": subtotal,
                "taxes": [],
                "shipping": 0,
                "total_taxes": 0,
                "grand_total": subtotal
            }

        tax_template = frappe.get_doc("Sales Taxes and Charges Template", tax_template_name)
        
        taxes_breakdown = []
        total_taxes = 0
        shipping = 0

        for tax in tax_template.taxes:
            if tax.charge_type == "Actual":
                # Fixed amount (e.g., shipping charges)
                amount = tax.tax_amount or 0
                # Check if this is shipping/delivery charge
                is_shipping = "shipping" in (tax.description or "").lower() or "delivery" in (tax.description or "").lower()
                
                if is_shipping:
                    # Don't add shipping to taxes array, handle separately
                    shipping = amount
                else:
                    # Add other fixed charges to taxes
                    taxes_breakdown.append({
                        "description": tax.description or tax.account_head,
                        "amount": amount,
                        "type": "fixed"
                    })
                total_taxes += amount
            elif tax.charge_type == "On Net Total":
                # Percentage on net total (e.g., GST)
                rate = tax.rate or 0
                amount = subtotal * (rate / 100)
                taxes_breakdown.append({
                    "description": tax.description or tax.account_head,
                    "amount": amount,
                    "rate": rate,
                    "type": "percentage"
                })
                total_taxes += amount

        grand_total = subtotal + total_taxes

        return {
            "subtotal": subtotal,
            "taxes": taxes_breakdown,
            "shipping": shipping,
            "total_taxes": total_taxes,
            "grand_total": grand_total
        }

    except Exception as e:
        frappe.log_error(f"Error calculating taxes: {str(e)}")
        # Return subtotal only if calculation fails
        return {
            "subtotal": subtotal,
            "taxes": [],
            "shipping": 0,
            "total_taxes": 0,
            "grand_total": subtotal
        }
