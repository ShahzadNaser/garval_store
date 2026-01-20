import frappe
from garval_store.utils import set_lang, get_all_products, get_item_groups, get_currency_symbol

def get_context(context):
    """Context for shop page - pulls products from ERPNext Items"""
    context.lang = set_lang()
    context.no_cache = 1
    context.currency_symbol = get_currency_symbol()

    # Get filter parameters
    sort = frappe.request.args.get('sort', 'newest')
    price_min = frappe.request.args.get('price_min')
    price_max = frappe.request.args.get('price_max')
    item_group = frappe.request.args.get('category')
    page = int(frappe.request.args.get('page', 1))

    # Pagination
    items_per_page = 12
    offset = (page - 1) * items_per_page

    # Build filters
    filters = {}
    if price_min:
        filters['price_min'] = float(price_min)
    if price_max:
        filters['price_max'] = float(price_max)
    if item_group:
        filters['item_group'] = item_group

    # Determine sort
    sort_map = {
        'newest': ('creation', 'desc'),
        'price_low': ('price', 'asc'),
        'price_high': ('price', 'desc'),
        'name': ('item_name', 'asc')
    }
    sort_by, sort_order = sort_map.get(sort, ('creation', 'desc'))

    # Get products
    products = get_all_products(
        filters=filters,
        limit=items_per_page,
        offset=offset,
        sort_by=sort_by if sort_by != 'price' else 'creation',
        sort_order=sort_order if sort_by != 'price' else 'desc'
    )

    # Sort by price if needed (since price might not be in the table)
    if sort_by == 'price':
        reverse = sort_order == 'desc'
        products.sort(key=lambda x: x.get('price', 0), reverse=reverse)

    # Get total count for pagination
    total_products = len(get_all_products(filters=filters, limit=1000))
    total_pages = (total_products + items_per_page - 1) // items_per_page

    context.products = products
    context.item_groups = get_item_groups()
    context.sort = sort
    context.price_min = price_min
    context.price_max = price_max
    context.selected_category = item_group
    context.current_page = page
    context.total_pages = total_pages

    return context
