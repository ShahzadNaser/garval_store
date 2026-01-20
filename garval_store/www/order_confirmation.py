import frappe
from garval_store.utils import set_lang, get_currency_symbol, get_customer_from_user

def get_context(context):
    """Context for order confirmation page"""
    try:
        context.lang = set_lang()
    except Exception as e:
        frappe.log_error(f"Error in set_lang: {str(e)}")
        context.lang = "es"

    context.no_cache = 1

    try:
        context.currency_symbol = get_currency_symbol()
    except Exception as e:
        frappe.log_error(f"Error in get_currency_symbol: {str(e)}")
        context.currency_symbol = "€"

    # Get order from URL parameter
    order_id = frappe.form_dict.get('order') if frappe.form_dict else None
    context.order = None

    if order_id and frappe.db.exists("Sales Order", order_id):
        # Verify ownership before showing order details
        if not _can_view_order(order_id):
            # User doesn't have permission to view this order
            context.order = None
            return context

        try:
            frappe.flags.ignore_permissions = True
            try:
                context.order = frappe.get_doc("Sales Order", order_id)
            finally:
                frappe.flags.ignore_permissions = False
        except Exception as e:
            # For any error, fetch order data using db queries
            frappe.flags.ignore_permissions = True
            try:
                order_data = frappe.db.get_value(
                    "Sales Order",
                    order_id,
                    ["name", "net_total", "grand_total", "total_taxes_and_charges"],
                    as_dict=True
                )
                if order_data:
                    # Get order items
                    items = frappe.db.get_all(
                        "Sales Order Item",
                        filters={"parent": order_id},
                        fields=["item_name", "qty", "amount"],
                        order_by="idx"
                    )
                    order_data['items'] = items

                    # Calculate net_total from items if not available
                    if not order_data.get('net_total'):
                        order_data['net_total'] = sum(item.get('amount', 0) for item in items)

                    # Get taxes
                    taxes = frappe.db.get_all(
                        "Sales Taxes and Charges",
                        filters={"parent": order_id},
                        fields=["description", "tax_amount", "rate"],
                        order_by="idx"
                    )
                    order_data['taxes'] = taxes
                    context.order = frappe._dict(order_data)
                else:
                    context.order = None
            except Exception as e2:
                frappe.log_error(f"Error fetching order: {str(e2)}")
                context.order = None
            finally:
                frappe.flags.ignore_permissions = False

    return context


def _can_view_order(order_id):
    """
    Check if current user can view the order.
    Returns True if:
    1. User is logged in and the order belongs to their linked customer
    2. Order was created very recently (within 5 minutes) - for immediate post-checkout confirmation
    """
    # Check 1: If user is logged in, verify they own the order
    if frappe.session.user and frappe.session.user != "Guest":
        customer = get_customer_from_user()
        if customer:
            order_customer = frappe.db.get_value("Sales Order", order_id, "customer")
            if order_customer == customer:
                return True

    # Check 2: Allow viewing if order was created very recently (within 5 minutes)
    # This handles the immediate redirect after checkout
    from frappe.utils import now_datetime, get_datetime
    order_creation = frappe.db.get_value("Sales Order", order_id, "creation")
    if order_creation:
        time_diff = now_datetime() - get_datetime(order_creation)
        if time_diff.total_seconds() < 300:  # 5 minutes
            return True

    return False