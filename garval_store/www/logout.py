import frappe

def get_context(context):
    """Logout and redirect to home"""
    from frappe.auth import LoginManager

    if frappe.session.user != "Guest":
        login_manager = LoginManager()
        login_manager.logout()

    frappe.local.flags.redirect_location = "/home"
    raise frappe.Redirect
