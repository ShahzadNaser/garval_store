import frappe
from frappe import _
from garval_store.utils import format_currency


@frappe.whitelist()
def send_order_confirmation(payment_request_name):
    """
    Send order confirmation email for a Payment Request.
    Called manually by admin after marking payment as paid.
    """
    payment_request = frappe.get_doc("Payment Request", payment_request_name)

    # Validate status
    if payment_request.status != "Paid":
        frappe.throw(_("Payment Request must be marked as Paid before sending order confirmation."))

    # Get the Sales Invoice
    if payment_request.reference_doctype != "Sales Invoice":
        frappe.throw(_("This Payment Request is not linked to a Sales Invoice."))

    sales_invoice = frappe.get_doc("Sales Invoice", payment_request.reference_name)

    # Get the Sales Order linked to this invoice
    sales_order_name = None
    for item in sales_invoice.items:
        if item.sales_order:
            sales_order_name = item.sales_order
            break

    if not sales_order_name:
        frappe.throw(_("No Sales Order found linked to this invoice."))

    sales_order = frappe.get_doc("Sales Order", sales_order_name)
    customer_email = payment_request.email_to

    if not customer_email:
        # Try to get email from customer
        customer_email = frappe.db.get_value("Customer", sales_order.customer, "email_id")

    if not customer_email:
        frappe.throw(_("No customer email found."))

    # Send the email
    _send_confirmation_email(sales_order, customer_email)

    frappe.msgprint(_("Order confirmation email sent to {0}").format(customer_email))

    return {"success": True, "email": customer_email}


def _send_confirmation_email(order, email):
    """Send order confirmation email with order details"""
    subject = _("Payment Confirmed - Order {0}").format(order.name)

    message = f"""
    <h2>{_('Payment Received - Thank You!')}</h2>
    <p>{_('We have received your payment for order')} <strong>{order.name}</strong>.</p>
    <p>{_('Your order is now being processed.')}</p>

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
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{int(item.qty)}</td>
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
        reference_doctype="Sales Order",
        reference_name=order.name,
        now=True
    )
