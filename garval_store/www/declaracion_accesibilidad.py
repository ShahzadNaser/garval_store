import frappe
from garval_store.utils import set_lang

def get_context(context):
    """Context for accessibility statement page"""
    context.lang = set_lang()
    context.no_cache = 1
    context.current_lang = context.lang
    return context

