import frappe
from garval_store.utils import set_lang, get_product_by_slug, get_featured_products

def get_context(context):
    """Context for product detail page - pulls from ERPNext Item"""
    context.lang = set_lang()
    context.no_cache = 1

    # Get product slug from URL
    slug = frappe.request.path.split('/product/')[-1] if '/product/' in frappe.request.path else None

    if not slug:
        # Try from form_dict (route rules)
        slug = frappe.form_dict.get('name')

    if not slug:
        frappe.throw("Product not found", frappe.DoesNotExistError)

    # Get product details
    product = get_product_by_slug(slug)

    if not product:
        frappe.throw("Product not found", frappe.DoesNotExistError)

    context.product = product

    # Get related products (exclude current)
    all_products = get_featured_products(limit=5)
    context.related_products = [p for p in all_products if p.item_code != product['item_code']][:4]

    return context
