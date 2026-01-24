import frappe
from frappe.utils import cint
from garval_store.utils import set_lang

def get_context(context):
    """Context for shop page - uses webshop functions"""
    context.lang = set_lang()
    context.no_cache = 1
    context.body_class = "product-page"
    context.parents = [{"name": frappe._("Home"), "route": "/"}]

    # Use webshop's ProductFiltersBuilder for filters
    from webshop.webshop.product_data_engine.filters import ProductFiltersBuilder
    from webshop.webshop.api import get_product_filter_data
    
    filter_engine = ProductFiltersBuilder()
    context.field_filters = filter_engine.get_field_filters()
    context.attribute_filters = filter_engine.get_attribute_filters()

    # Get page length from webshop settings
    page_length = (
        cint(frappe.db.get_single_value("Webshop Settings", "products_per_page")) or 20
    )
    context.page_length = page_length

    # Get filter parameters from request
    sort = frappe.request.args.get('sort', 'newest')
    price_min = frappe.request.args.get('price_min')
    price_max = frappe.request.args.get('price_max')
    item_group = frappe.request.args.get('category')
    page = int(frappe.request.args.get('page', 1))
    start = (page - 1) * page_length

    # Build field filters for webshop API
    field_filters = {}
    if item_group:
        field_filters['item_group'] = item_group

    # Get products using webshop's API
    query_args = {
        "start": start,
        "field_filters": field_filters
    }
    
    result = get_product_filter_data(query_args)
    items = result.get("items", [])
    items_count = result.get("items_count", 0)

    # Apply price filters if specified
    if price_min or price_max:
        filtered_items = []
        for item in items:
            price = item.get("price_list_rate") or 0
            if price_min and price < float(price_min):
                continue
            if price_max and price > float(price_max):
                continue
            filtered_items.append(item)
        items = filtered_items

    # Apply sorting
    if sort == 'price_low':
        items.sort(key=lambda x: x.get("price_list_rate", 0))
    elif sort == 'price_high':
        items.sort(key=lambda x: x.get("price_list_rate", 0), reverse=True)
    elif sort == 'name':
        items.sort(key=lambda x: (x.get("web_item_name") or x.get("item_name") or "").lower())

    # Format products for template
    products = []
    for item in items:
        # Check stock status - webshop returns in_stock as 0 or 1 (or False/True)
        in_stock = item.get("in_stock")
        if in_stock is None:
            # If not set, check if it's a stock item - if yes, assume out of stock if no stock_qty
            is_stock_item = item.get("is_stock_item", False)
            out_of_stock = bool(is_stock_item and item.get("stock_qty", 0) == 0)
        else:
            # in_stock is 0 (out) or 1 (in stock)
            out_of_stock = not bool(in_stock)
        
        product = {
            "item_code": item.get("item_code"),
            "name": item.get("web_item_name") or item.get("item_name"),
            "slug": item.get("route") or item.get("item_code"),
            "image": item.get("website_image") or item.get("image"),
            "price": item.get("price_list_rate") or 0,
            "formatted_price": item.get("formatted_price") or "€0.00",
            "out_of_stock": out_of_stock
        }
        products.append(product)

    # Calculate pagination
    total_pages = (items_count + page_length - 1) // page_length

    context.products = products
    context.sort = sort
    context.price_min = price_min
    context.price_max = price_max
    context.selected_category = item_group
    context.current_page = page
    context.total_pages = total_pages

    return context
