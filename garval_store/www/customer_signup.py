import frappe
from frappe.utils import cint
from garval_store.utils import set_lang

def get_context(context):
    """Context for signup page"""
    context.lang = set_lang()
    context.no_cache = 1

    # Redirect if already logged in
    if frappe.session.user != "Guest":
        frappe.local.flags.redirect_location = "/my-account"
        raise frappe.Redirect

    # Password policy settings
    context.enable_password_policy = cint(frappe.get_system_settings("enable_password_policy"))
    context.minimum_password_score = cint(frappe.get_system_settings("minimum_password_score") or 2)

    return context
