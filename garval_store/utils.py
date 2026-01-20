import frappe
from frappe import _

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
    """Get featured products from ERPNext Items"""
    try:
        # Try Website Item first (ERPNext e-commerce)
        if frappe.db.exists("DocType", "Website Item"):
            products = frappe.get_all(
                "Website Item",
                filters={
                    "published": 1,
                },
                fields=[
                    "name", "item_code", "item_name", "web_item_name",
                    "short_description", "website_image", "route",
                    "website_warehouse", "on_backorder"
                ],
                order_by="ranking desc, modified desc",
                limit=limit
            )

            for product in products:
                product.slug = product.route or product.item_code
                product.name = product.web_item_name or product.item_name
                # Get image from Website Item, fallback to Item image
                product.image = product.website_image
                if not product.image:
                    item_image = frappe.db.get_value("Item", product.item_code, "image")
                    product.image = item_image
                product.description = product.short_description
                # Check stock if warehouse is specified
                product.out_of_stock = False
                if product.get('website_warehouse'):
                    product.out_of_stock = not has_stock(product.item_code, product.website_warehouse)
                elif product.get('on_backorder'):
                    product.out_of_stock = False  # Allow backorders

                # Get price
                price_info = get_item_price(product.item_code)
                product.price = price_info.get('price', 0)
                company = frappe.db.get_single_value("Global Defaults", "default_company")
                product.formatted_price = price_info.get('formatted_price', format_currency(0, company))

            return products

        # Fallback to regular Items
        products = frappe.get_all(
            "Item",
            filters={
                "disabled": 0,
                "is_sales_item": 1,
                "show_in_website": 1
            },
            fields=[
                "name", "item_code", "item_name", "description",
                "image", "stock_uom"
            ],
            order_by="modified desc",
            limit=limit
        )

        for product in products:
            product.slug = product.item_code
            product.name = product.item_name
            product.out_of_stock = not has_stock(product.item_code)

            price_info = get_item_price(product.item_code)
            product.price = price_info.get('price', 0)
            product.formatted_price = price_info.get('formatted_price', '€0.00')

        return products

    except Exception as e:
        frappe.log_error(f"Error fetching products: {str(e)}")
        return []

def get_all_products(filters=None, limit=20, offset=0, sort_by="modified", sort_order="desc"):
    """Get all products with filters for shop page"""
    try:
        base_filters = {"disabled": 0, "is_sales_item": 1}

        if frappe.db.exists("DocType", "Website Item"):
            base_filters = {"published": 1}
            doctype = "Website Item"
            fields = [
                "name", "item_code", "item_name", "web_item_name",
                "short_description", "website_image", "route",
                "website_warehouse", "on_backorder"
            ]
        else:
            doctype = "Item"
            base_filters["show_in_website"] = 1
            fields = [
                "name", "item_code", "item_name", "description", "image"
            ]

        # Apply custom filters
        if filters:
            if filters.get('item_group'):
                base_filters['item_group'] = filters.get('item_group')

        products = frappe.get_all(
            doctype,
            filters=base_filters,
            fields=fields,
            order_by=f"{sort_by} {sort_order}",
            limit_start=offset,
            limit_page_length=limit
        )

        for product in products:
            if doctype == "Website Item":
                product.slug = product.route or product.item_code
                product.name = product.web_item_name or product.item_name
                # Get image from Website Item, fallback to Item image
                product.image = product.website_image
                if not product.image:
                    item_image = frappe.db.get_value("Item", product.item_code, "image")
                    product.image = item_image
                # Check stock if warehouse is specified
                product.out_of_stock = False
                if product.get('website_warehouse'):
                    product.out_of_stock = not has_stock(product.item_code, product.website_warehouse)
                elif product.get('on_backorder'):
                    product.out_of_stock = False  # Allow backorders
            else:
                product.slug = product.item_code
                product.name = product.item_name
                product.out_of_stock = not has_stock(product.item_code)

            price_info = get_item_price(product.item_code)
            product.price = price_info.get('price', 0)
            product.formatted_price = price_info.get('formatted_price', '€0.00')

        # Apply price filter client-side friendly
        if filters:
            price_min = filters.get('price_min')
            price_max = filters.get('price_max')
            if price_min:
                products = [p for p in products if p.price >= float(price_min)]
            if price_max:
                products = [p for p in products if p.price <= float(price_max)]

        return products

    except Exception as e:
        frappe.log_error(f"Error fetching products: {str(e)}")
        return []

def get_product_by_slug(slug):
    """Get single product by slug/route"""
    try:
        if frappe.db.exists("DocType", "Website Item"):
            product = frappe.get_doc("Website Item", {"route": slug})
            # Check stock availability
            out_of_stock = False
            if product.website_warehouse:
                out_of_stock = not has_stock(product.item_code, product.website_warehouse)

            return {
                "item_code": product.item_code,
                "name": product.web_item_name or product.item_name,
                "description": product.web_long_description or product.short_description,
                "short_description": product.short_description,
                "image": product.website_image,
                "images": get_product_images(product.name, "Website Item"),
                "price": get_item_price(product.item_code).get('price', 0),
                "formatted_price": get_item_price(product.item_code).get('formatted_price', format_currency(0)),
                "out_of_stock": out_of_stock,
                "uom": product.stock_uom
            }
        else:
            # Try by item_code
            if frappe.db.exists("Item", slug):
                product = frappe.get_doc("Item", slug)
                return {
                    "item_code": product.item_code,
                    "name": product.item_name,
                    "description": product.description,
                    "short_description": product.description[:200] if product.description else "",
                    "image": product.image,
                    "images": [],
                    "price": get_item_price(product.item_code).get('price', 0),
                    "formatted_price": get_item_price(product.item_code).get('formatted_price', format_currency(0)),
                    "out_of_stock": not has_stock(product.item_code),
                    "uom": product.stock_uom
                }
    except Exception as e:
        frappe.log_error(f"Error fetching product {slug}: {str(e)}")

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
            price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")

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
        frappe.db.commit()

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
        email_verified = frappe.db.get_value("User", frappe.session.user, "email_verified")
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
            "order_type": "Sales",
            "contact_email": customer_info.get("email"),
            "contact_mobile": customer_info.get("phone"),
            "items": []
        })

        # Add validated items to Sales Order
        for item in validated_items:
            so.append("items", item)

        # Add shipping address if provided
        if customer_info.get("selected_address"):
            # Use existing address
            so.shipping_address_name = customer_info.get("selected_address")
        elif customer_info.get("address"):
            # Fallback: Create address from form fields (legacy support)
            address = frappe.get_doc({
                "doctype": "Address",
                "address_title": customer_info.get("full_name"),
                "address_type": "Shipping",
                "address_line1": customer_info.get("address"),
                "city": customer_info.get("city", ""),
                "country": customer_info.get("country", "Spain"),
                "pincode": customer_info.get("postal_code", ""),
                "links": [{
                    "link_doctype": "Customer",
                    "link_name": customer
                }]
            })
            address.insert(ignore_permissions=True)
            so.shipping_address_name = address.name

        # Apply taxes template to Sales Order
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
        
        # Calculate totals (this will calculate taxes and grand total)
        so.calculate_taxes_and_totals()

        so.insert(ignore_permissions=True)
        so.submit()

        # Create Payment Request if payment gateway is provided
        payment_url = None
        payment_gateway = customer_info.get("payment_method")

        if payment_gateway and payment_gateway != "Manual":
            si_doc = None
            try:
                # Step 1: Create Sales Invoice from Sales Order (Proper ERPNext flow)
                # This is EXACTLY how UI does it
                from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
                si_doc = make_sales_invoice(so.name, ignore_permissions=True)
                
                # Ensure set_missing_values and calculate_taxes_and_totals are called (like UI does)
                si_doc.run_method("set_missing_values")
                si_doc.run_method("calculate_taxes_and_totals")
                
                si_doc.insert(ignore_permissions=True)
                si_doc.flags.ignore_permissions = True
                si_doc.submit()
                
                # Reload to get correct outstanding_amount after submit
                si_doc.reload()
                
                # Get payment gateway account
                payment_gateway_account = frappe.get_doc("Payment Gateway Account", payment_gateway)

                # Check if Payment Gateway has a controller (Bank Transfer doesn't)
                pg_controller = frappe.db.get_value("Payment Gateway", payment_gateway_account.payment_gateway, "gateway_controller")
                is_bank_transfer = not pg_controller or "Bank Transfer" in str(payment_gateway_account.payment_gateway)
                
                # For Bank Transfer: Create Payment Request
                if is_bank_transfer:
                    # Get first enabled bank account for company (don't check is_company_account)
                    bank_account = frappe.db.get_value(
                        "Bank Account",
                        {"company": company, "disabled": 0},
                        "name",
                        order_by="is_default desc, creation desc"
                    )
                    
                    if not bank_account:
                        frappe.throw(_("No company bank account found for Bank Transfer. Please configure one."))
                    
                    # Create Payment Request from Sales Invoice
                    # Use outstanding_amount instead of grand_total for Payment Request
                    # Get message and subject from Payment Gateway Account (like UI does)
                    pr_message = payment_gateway_account.message or _("Payment request for invoice {0}").format(si_doc.name)
                    pr_subject = getattr(payment_gateway_account, "subject", None) or _("Invoice pending for {0}").format(so.name)
                    
                    pr = frappe.get_doc({
                        "doctype": "Payment Request",
                        "payment_gateway_account": payment_gateway_account.name,
                        "payment_gateway": payment_gateway_account.payment_gateway,
                        "payment_account": payment_gateway_account.payment_account,
                        "currency": si_doc.currency,
                        "grand_total": si_doc.outstanding_amount,
                        "mode_of_payment": payment_gateway_account.payment_gateway,
                        "email_to": customer_info.get("email"),
                        "subject": pr_subject,
                        "message": pr_message,
                        "reference_doctype": "Sales Invoice",
                        "reference_name": si_doc.name,
                        "party_type": "Customer",
                        "party": customer,
                        "bank_account": bank_account
                    })
                    pr.insert(ignore_permissions=True)
                    pr.submit()
                    
                    payment_url = None  # No payment URL for Bank Transfer
                    
                else:
                    # For other payment gateways: Create Payment Request
                    # Get or create Mode of Payment
                    mode_of_payment = payment_gateway_account.payment_gateway
                    if not frappe.db.exists("Mode of Payment", mode_of_payment):
                        mop = frappe.get_doc({
                            "doctype": "Mode of Payment",
                            "mode_of_payment": mode_of_payment,
                            "type": "General"
                        })
                        mop.insert(ignore_permissions=True)

                    # Create Payment Request from Sales Invoice
                    # Use outstanding_amount instead of grand_total for Payment Request
                    # Get message and subject from Payment Gateway Account (like UI does)
                    pr_message = payment_gateway_account.message or _("Payment request for invoice {0}").format(si_doc.name)
                    pr_subject = getattr(payment_gateway_account, "subject", None) or _("Payment Request for {0}").format(si_doc.name)

                    pr = frappe.get_doc({
                        "doctype": "Payment Request",
                        "payment_gateway_account": payment_gateway_account.name,
                        "payment_gateway": payment_gateway_account.payment_gateway,
                        "payment_account": payment_gateway_account.payment_account,
                        "currency": payment_gateway_account.currency or si_doc.currency,
                        "grand_total": si_doc.outstanding_amount,
                        "mode_of_payment": mode_of_payment,
                        "email_to": customer_info.get("email"),
                        "subject": pr_subject,
                        "message": pr_message,
                        "reference_doctype": "Sales Invoice",
                        "reference_name": si_doc.name,
                        "party_type": "Customer",
                        "party": customer,
                        "mute_email": 1  # Don't send email, we're redirecting directly
                    })
                    pr.insert(ignore_permissions=True)
                    pr.submit()
                    
                    # Generate payment URL
                    payment_url = None
                    try:
                        pr.reload()
                        payment_url = pr.payment_url
                        if not payment_url:
                            pr.set_payment_request_url()
                            payment_url = pr.payment_url
                    except Exception as url_error:
                        frappe.log_error(f"Payment URL generation failed: {str(url_error)}", "Payment URL Error")
                        payment_url = None

            except Exception as e:
                error_msg = f"Error creating payment request: {str(e)}\nTraceback: {frappe.get_traceback()}\nPayment Gateway: {payment_gateway}"
                frappe.log_error(error_msg, "Payment Error")
                
                # Cancel Sales Invoice if it was created
                if si_doc:
                    try:
                        si_doc.reload()
                        if si_doc.docstatus == 1:  # If submitted
                            si_doc.cancel()
                            frappe.log_error(f"Cancelled Sales Invoice {si_doc.name} due to payment error", "Payment Error")
                    except Exception as cancel_error:
                        frappe.log_error(f"Error cancelling Sales Invoice: {str(cancel_error)}", "Payment Error")
                
                # Cancel Sales Order
                try:
                    so.reload()
                    if so.docstatus == 1:  # If submitted
                        so.cancel()
                        frappe.log_error(f"Cancelled Sales Order {so.name} due to payment error", "Payment Error")
                except Exception as cancel_error:
                    frappe.log_error(f"Error cancelling Sales Order: {str(cancel_error)}", "Payment Error")
                
                frappe.db.rollback()
                
                # Return specific error message
                error_detail = str(e)
                if "Settings not found" in error_detail:
                    return {
                        "success": False,
                        "error": _("Payment gateway configuration error. Please contact support.")
                    }
                else:
                    return {
                        "success": False,
                        "error": _("Failed to process payment: {0}").format(error_detail)
                    }

        frappe.db.commit()

        return {
            "success": True,
            "order_id": so.name,
            "order": so.as_dict(),
            "payment_url": payment_url
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
