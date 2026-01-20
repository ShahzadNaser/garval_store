import frappe
from frappe import _
from frappe.apps import get_default_path


def on_user_login(login_manager):
    """Create Customer record on login if not exists (for SSO users)"""
    user = login_manager.user

    # Skip for Administrator and Guest
    if user in ("Administrator", "Guest"):
        return

    # Use ignore_permissions instead of switching users - this preserves session integrity
    try:
        # Only auto-verify email for actual SSO users (those with social login configured)
        # Regular email/password users must verify via the email link
        if not frappe.db.get_value("User", user, "email_verified"):
            # Check if user has any social login configured
            has_social_login = frappe.db.exists("User Social Login", {"parent": user})
            if has_social_login:
                frappe.db.set_value("User", user, "email_verified", 1, update_modified=False)

        # Check if customer already exists for this user
        from garval_store.utils import get_customer_from_user
        customer = get_customer_from_user(user)

        if customer:
            return  # Customer already exists

        # Get user details
        user_doc = frappe.get_doc("User", user)
        full_name = user_doc.full_name or user_doc.first_name or user

        # Create Customer
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": full_name,
            "customer_type": "Individual",
            "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual",
            "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
            "email_id": user
        })
        customer.insert(ignore_permissions=True)

        # Add Customer role to user
        if "Customer" not in [r.role for r in user_doc.roles]:
            user_doc.append("roles", {"role": "Customer"})
            user_doc.save(ignore_permissions=True)

        # Create Contact and Link
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": user_doc.first_name or full_name.split()[0],
            "last_name": user_doc.last_name or " ".join(full_name.split()[1:]) or "",
            "user": user,
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer.name
            }]
        })
        contact.append("email_ids", {
            "email_id": user,
            "is_primary": 1
        })
        contact.insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Failed to create customer on login for {user}: {str(e)}\n{frappe.get_traceback()}", "Customer Creation Error")


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
