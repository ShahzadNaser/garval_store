import frappe
from garval_store.utils import set_lang

def get_context(context):
    """Context for privacy policy page"""
    context.lang = set_lang()
    context.no_cache = 1
    # Add lang to context for template use
    context.current_lang = context.lang
    return context

