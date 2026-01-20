import frappe
from garval_store.utils import set_lang, get_currency_symbol

def get_context(context):
    """Context for cart page"""
    context.lang = set_lang()
    context.no_cache = 1
    context.currency_symbol = get_currency_symbol()
    return context
