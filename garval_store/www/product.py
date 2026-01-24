import frappe
from garval_store.utils import set_lang

def get_context(context):
    """Context for product detail page - uses webshop's WebsiteItem.get_context()"""
    context.lang = set_lang()
    context.no_cache = 1

    # Get product slug from URL
    slug = frappe.form_dict.get('name', '').strip()
    
    # If form_dict doesn't have it, parse from path
    if not slug:
        path = frappe.request.path
        if '/product/' in path:
            slug = path.split('/product/')[-1].split('?')[0].rstrip('/')
        elif path.endswith('/product') or path == '/product':
            slug = None

    if not slug:
        frappe.throw("Product not found - no slug in URL", frappe.DoesNotExistError)

    # Find Website Item by route (webshop's way)
    website_item_name = frappe.db.get_value("Website Item", {"route": slug}, "name")
    
    # If not found by exact route, try LIKE match
    if not website_item_name:
        website_items = frappe.db.get_all(
            "Website Item",
            filters={"route": ["like", f"{slug}%"]},
            fields=["name"],
            limit=1
        )
        if website_items:
            website_item_name = website_items[0].name
    
    # If still not found, try by item_code
    if not website_item_name:
        if frappe.db.exists("Item", slug):
            website_item_name = frappe.db.get_value("Website Item", {"item_code": slug}, "name")
    
    # If still not found, try by Website Item name
    if not website_item_name:
        if frappe.db.exists("Website Item", slug):
            website_item_name = slug
    
    if not website_item_name:
        frappe.throw(f"Product not found: {slug}", frappe.DoesNotExistError)

    # Get Website Item document and use webshop's get_context() method
    from webshop.webshop.doctype.website_item.website_item import WebsiteItem
    
    website_item = frappe.get_doc("Website Item", website_item_name)
    
    # Use webshop's get_context() method - this handles everything including stock via set_shopping_cart_data()
    website_item.get_context(context)
    
    # Add product data for template compatibility
    product_info = context.shopping_cart.get("product_info", {})
    
    # Get stock status - webshop returns in_stock as 0 or 1 (or False/True)
    in_stock = product_info.get("in_stock")
    # Convert to boolean: 0/False = out of stock, 1/True = in stock
    if in_stock is None:
        # If not set, check if it's a stock item - if yes, assume out of stock if no stock_qty
        is_stock_item = frappe.db.get_value("Item", website_item.item_code, "is_stock_item")
        out_of_stock = bool(is_stock_item and product_info.get("stock_qty", 0) == 0)
    else:
        # in_stock is 0 (out) or 1 (in stock)
        out_of_stock = not bool(in_stock)
    
    context.product = {
        "item_code": website_item.item_code,
        "name": website_item.web_item_name or website_item.item_name,
        "description": website_item.web_long_description or website_item.short_description,
        "short_description": website_item.short_description,
        "image": website_item.website_image or frappe.db.get_value("Item", website_item.item_code, "image"),
        "price": product_info.get("price", {}).get("price_list_rate") or 0,
        "formatted_price": product_info.get("price", {}).get("formatted_price") or "€0.00",
        "out_of_stock": out_of_stock,
        "in_stock": bool(in_stock) if in_stock is not None else False,
        "stock_qty": product_info.get("stock_qty", 0),
        "uom": product_info.get("uom") or website_item.stock_uom,
        "on_backorder": product_info.get("on_backorder", False),
        "is_stock_item": product_info.get("is_stock_item", False)
    }
    
    # Get related products
    from webshop.webshop.api import get_product_filter_data
    result = get_product_filter_data({"start": 0, "field_filters": {}})
    all_items = result.get("items", [])[:5]
    
    context.related_products = [
        {
            "item_code": item.get("item_code"),
            "name": item.get("web_item_name") or item.get("item_name"),
            "slug": item.get("route") or item.get("item_code"),
            "image": item.get("website_image") or item.get("image"),
            "formatted_price": item.get("formatted_price") or "€0.00"
        }
        for item in all_items 
        if item.get("item_code") != website_item.item_code
    ][:4]

    return context
