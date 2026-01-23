import frappe
from frappe import _
from frappe.apps import get_default_path
from garval_store.utils import get_email_verified, set_email_verified


def on_session_creation(login_manager):
    """Run cart setup - use ignore_permissions to avoid breaking session"""
    user = login_manager.user

    # Skip for Administrator and Guest
    if user in ("Administrator", "Guest"):
        return

    # Don't switch users - just call the functions with proper error handling
    # The webshop functions should work with ignore_permissions or current user context
    try:
        from webshop.webshop.shopping_cart.utils import set_cart_count
        set_cart_count(login_manager)
    except Exception as e:
        frappe.log_error(f"set_cart_count failed for {user}: {str(e)}", "Cart Setup Warning")

    try:
        from webshop.webshop.utils.portal import update_debtors_account
        update_debtors_account()
    except Exception as e:
        frappe.log_error(f"update_debtors_account failed for {user}: {str(e)}", "Cart Setup Warning")
