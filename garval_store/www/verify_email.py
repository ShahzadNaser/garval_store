import frappe
from garval_store.utils import set_lang


def get_context(context):
    """Context for email verification page"""
    context.lang = set_lang()
    context.no_cache = 1

    # Get parameters from URL
    key = frappe.form_dict.get('key')
    email = frappe.form_dict.get('email')

    context.verification_attempted = False
    context.verification_success = False
    context.verification_error = None
    context.already_verified = False

    if key and email:
        context.verification_attempted = True
        # Verify the email
        from garval_store.api.auth import verify_email
        result = verify_email(key, email)

        if result.get("success"):
            context.verification_success = True
            context.already_verified = result.get("already_verified", False)
        else:
            context.verification_error = result.get("error")

    return context
