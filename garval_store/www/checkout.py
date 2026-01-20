import frappe
from garval_store.utils import set_lang, get_customer_from_user, get_payment_gateways, get_currency_symbol

def get_context(context):
    """Context for checkout page"""
    context.lang = set_lang()
    context.no_cache = 1
    context.currency_symbol = get_currency_symbol()

    # Get customer if logged in
    customer_name = get_customer_from_user()
    if customer_name:
        context.customer = frappe.get_doc("Customer", customer_name)

        # Get customer's saved addresses
        context.addresses = frappe.get_all(
            "Address",
            filters={
                "link_doctype": "Customer",
                "link_name": customer_name
            },
            fields=["name", "address_title", "address_line1", "address_line2", "city", "state", "pincode", "country", "phone"]
        )
    else:
        context.customer = None
        context.addresses = []

    # Get enabled payment gateways
    context.payment_gateways = get_payment_gateways()

    return context
