import frappe
from garval_store.utils import set_lang, get_customer_from_user, get_customer_orders, get_currency_symbol, require_email_verification

def get_context(context):
    """Context for my account page - shows ERPNext Sales Orders"""
    # Require email verification
    require_email_verification()
    
    context.lang = set_lang()
    context.no_cache = 1
    context.currency_symbol = get_currency_symbol()

    # Get customer
    customer_name = get_customer_from_user()
    if customer_name:
        context.customer = frappe.get_doc("Customer", customer_name)

        # Get orders
        context.orders = get_customer_orders(customer_name, limit=20)

        # Get addresses
        context.addresses = get_customer_addresses(customer_name)
    else:
        context.customer = None
        context.orders = []
        context.addresses = []

    return context

def get_customer_addresses(customer):
    """Get addresses linked to customer"""
    try:
        addresses = frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"},
            fields=["parent"]
        )

        address_list = []
        for addr in addresses:
            address = frappe.get_doc("Address", addr.parent)
            address_list.append({
                "name": address.name,
                "address_title": address.address_title,
                "address_type": address.address_type,
                "address_line1": address.address_line1,
                "address_line2": address.address_line2,
                "city": address.city,
                "state": address.state,
                "pincode": address.pincode,
                "country": address.country,
                "phone": address.phone
            })

        return address_list
    except:
        return []
