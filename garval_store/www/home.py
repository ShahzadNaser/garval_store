import frappe
from garval_store.utils import set_lang, get_featured_products, get_currency_symbol

def get_context(context):
    """Context for home page - pulls featured products from ERPNext Items"""
    context.lang = set_lang()
    context.no_cache = 1
    context.currency_symbol = get_currency_symbol()

    # Get featured products from ERPNext Website Item or Item
    context.products = get_featured_products(limit=4)

    return context
