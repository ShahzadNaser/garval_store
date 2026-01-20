import frappe
from garval_store.utils import set_lang
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
from frappe.utils.password import get_decrypted_password

def get_context(context):
    """Context for login page"""
    context.lang = set_lang()
    context.no_cache = 1

    # Get redirect URL - check both request args and form_dict
    redirect_to = (frappe.local.request.args.get("redirect-to") 
                   or frappe.local.request.args.get("redirect_to")
                   or frappe.form_dict.get("redirect-to") 
                   or frappe.form_dict.get("redirect_to") 
                   or "/my-account")

    # Redirect if already logged in
    if frappe.session.user != "Guest":
        frappe.local.flags.redirect_location = redirect_to
        raise frappe.Redirect

    # Get OAuth providers (Google)
    context["provider_logins"] = []
    providers = frappe.get_all(
        "Social Login Key",
        filters={"enable_social_login": 1},
        fields=["name", "client_id", "base_url", "provider_name"],
        ignore_permissions=True,
    )

    for provider in providers:
        if provider.provider_name and provider.provider_name.lower() == "google":
            client_secret = get_decrypted_password("Social Login Key", provider.name, "client_secret", raise_exception=False)
            if client_secret and provider.client_id and provider.base_url and get_oauth_keys(provider.name):
                context["provider_logins"].append({
                    "provider_name": provider.provider_name,
                    "auth_url": get_oauth2_authorize_url(provider.name, redirect_to),
                })
                break

    context["redirect_to"] = redirect_to
    return context
