import frappe
from garval_store.utils import set_lang, get_currency_symbol, require_email_verification

def get_context(context):
    """Context for cart page"""
    # Require email verification for cart (to place orders)
    require_email_verification()
    
    context.lang = set_lang()
    context.no_cache = 1
    context.currency_symbol = get_currency_symbol()
    return context
