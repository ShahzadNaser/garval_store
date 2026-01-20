import frappe
from frappe import _
from garval_store.utils import create_sales_order_from_cart, calculate_taxes_and_charges, format_currency

@frappe.whitelist(allow_guest=True)
def create_order(customer_info, items, total):
    """Create ERPNext Sales Order from checkout"""
    try:
        if isinstance(customer_info, str):
            import json
            customer_info = json.loads(customer_info)
        if isinstance(items, str):
            import json
            items = json.loads(items)

        cart_data = {
            "items": items,
            "total": float(total)
        }

        result = create_sales_order_from_cart(cart_data, customer_info)

        if result.get("success"):
            # Order confirmation email is now sent when payment is marked as paid
            # Invoice email with bank details is sent via Payment Request on submit
            return {
                "success": True,
                "order_id": result.get("order_id"),
                "payment_url": result.get("payment_url"),
                "message": _("Order placed successfully")
            }
        else:
            return {
                "success": False,
                "error": result.get("error", _("Failed to create order"))
            }

    except Exception as e:
        frappe.log_error(f"Create order error: {str(e)}")
        return {
            "success": False,
            "error": _("Failed to process order. Please try again.")
        }

def send_order_confirmation(order_id, email):
    """Send order confirmation email"""
    try:
        order = frappe.get_doc("Sales Order", order_id)

        subject = _("Order Confirmation - {0}").format(order_id)

        message = f"""
        <h2>{_('Thank you for your order!')}</h2>
        <p>{_('Your order')} <strong>{order_id}</strong> {_('has been received.')}</p>

        <h3>{_('Order Details')}</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #f5f5f5;">
                <th style="padding: 10px; text-align: left;">{_('Product')}</th>
                <th style="padding: 10px; text-align: right;">{_('Qty')}</th>
                <th style="padding: 10px; text-align: right;">{_('Price')}</th>
            </tr>
        """

        for item in order.items:
            message += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.item_name}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{item.qty}</td>
                <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{format_currency(item.amount)}</td>
            </tr>
            """

        message += f"""
        </table>

        <p style="margin-top: 20px; font-size: 18px;">
            <strong>{_('Total')}: {format_currency(order.grand_total)}</strong>
        </p>

        <p>{_('We will notify you when your order ships.')}</p>

        <p>{_('Best regards,')}<br>Finca Garval</p>
        """

        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=message,
            now=True
        )

    except Exception as e:
        frappe.log_error(f"Order email error: {str(e)}")

@frappe.whitelist(allow_guest=True)
def get_shipping_rates(country, postal_code=None):
    """Get shipping rates based on location"""
    try:
        # Simple shipping logic - can be extended
        shipping_rates = {
            "Spain": {"standard": 0, "express": 5.99},  # Free shipping in Spain
            "Portugal": {"standard": 4.99, "express": 9.99},
            "France": {"standard": 7.99, "express": 14.99},
            "Germany": {"standard": 9.99, "express": 17.99},
            "Italy": {"standard": 9.99, "express": 17.99},
            "default": {"standard": 14.99, "express": 24.99}
        }

        rates = shipping_rates.get(country, shipping_rates["default"])

        return {
            "success": True,
            "rates": [
                {
                    "id": "standard",
                    "name": _("Standard Shipping"),
                    "price": rates["standard"],
                    "days": "5-7"
                },
                {
                    "id": "express",
                    "name": _("Express Shipping"),
                    "price": rates["express"],
                    "days": "2-3"
                }
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist(allow_guest=True)
def calculate_taxes(subtotal):
    """Calculate taxes and charges for checkout page"""
    try:
        subtotal = float(subtotal)
        result = calculate_taxes_and_charges(subtotal)
        return {
            "success": True,
            **result
        }
    except Exception as e:
        frappe.log_error(f"Calculate taxes error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
