import frappe
from frappe import _
from garval_store.utils import get_customer_from_user


@frappe.whitelist(allow_guest=False)
def get_payment_url(order_id):
    """
    Get or create payment URL for an existing Sales Order.
    Returns the payment URL so user can pay for "To Pay" orders.
    """
    try:
        # Get the Sales Order
        so = frappe.get_doc("Sales Order", order_id)

        # Verify the order belongs to the current user
        customer = get_customer_from_user()
        if not customer or so.customer != customer:
            return {"success": False, "error": _("You don't have permission to access this order")}

        # Check if order is in "To Pay" status
        if so.status != "To Pay":
            return {"success": False, "error": _("This order is not in 'To Pay' status")}

        # Step 1: Check if Sales Invoice exists, if not create it
        existing_invoice = frappe.db.get_value(
            "Sales Invoice Item",
            {"sales_order": order_id, "docstatus": 1},
            "parent",
            order_by="creation desc"
        )
        
        if not existing_invoice:
            # Create Sales Invoice from Sales Order
            from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
            si_doc = make_sales_invoice(order_id, ignore_permissions=True)
            si_doc.insert(ignore_permissions=True)
            si_doc.flags.ignore_permissions = True
            si_doc.submit()
            existing_invoice = si_doc.name
            frappe.db.commit()
        
        # Step 2: Check if Payment Request already exists for this Sales Invoice
        existing_pr = frappe.db.get_value(
            "Payment Request",
            {
                "reference_doctype": "Sales Invoice",
                "reference_name": existing_invoice,
                "docstatus": ["!=", 2]  # Not cancelled
            },
            "name",
            order_by="creation desc"
        )

        if existing_pr:
            # Use existing Payment Request
            pr = frappe.get_doc("Payment Request", existing_pr)
            if not pr.payment_url:
                pr.set_payment_request_url()
                pr.save(ignore_permissions=True)
                frappe.db.commit()
            payment_url = pr.payment_url
        else:
            # Create new Payment Request from Sales Invoice
            si_doc = frappe.get_doc("Sales Invoice", existing_invoice)
            
            # Get payment gateway account (use first available Stripe gateway)
            payment_gateway_account = frappe.db.get_value(
                "Payment Gateway Account",
                {"payment_gateway": ["like", "Stripe%"]},
                "name",
                order_by="creation desc"
            )

            if not payment_gateway_account:
                return {"success": False, "error": _("No payment gateway configured. Please contact support.")}

            pga = frappe.get_doc("Payment Gateway Account", payment_gateway_account)

            # Get or create Mode of Payment
            mode_of_payment = pga.payment_gateway
            if not frappe.db.exists("Mode of Payment", mode_of_payment):
                mop = frappe.get_doc({
                    "doctype": "Mode of Payment",
                    "mode_of_payment": mode_of_payment,
                    "type": "General"
                })
                mop.insert(ignore_permissions=True)

            # Create Payment Request from Sales Invoice (not from Sales Order)
            pr = frappe.get_doc({
                "doctype": "Payment Request",
                "payment_gateway_account": pga.name,
                "payment_gateway": pga.payment_gateway,
                "payment_account": pga.payment_account,
                "currency": pga.currency or si_doc.currency,
                "grand_total": si_doc.grand_total,
                "mode_of_payment": mode_of_payment,
                "email_to": frappe.session.user,
                "subject": _("Payment Request for {0}").format(si_doc.name),
                "message": _("Payment request for invoice {0}").format(si_doc.name),
                "reference_doctype": "Sales Invoice",  # Reference Sales Invoice, not Sales Order
                "reference_name": si_doc.name,
                "party_type": "Customer",
                "party": so.customer,
                "mute_email": 1
            })
            pr.insert(ignore_permissions=True)
            pr.submit()

            # Generate payment URL
            pr.set_payment_request_url()
            payment_url = pr.payment_url
            frappe.db.commit()

        return {
            "success": True,
            "payment_url": payment_url
        }

    except Exception as e:
        frappe.log_error(f"Error getting payment URL: {str(e)}\nOrder: {order_id}\nTraceback: {frappe.get_traceback()}", "Get Payment URL Error")
        return {"success": False, "error": _("Failed to get payment link. Please try again or contact support.")}


@frappe.whitelist(allow_guest=False)
def cancel_order(order_id):
    """
    Cancel an unpaid Sales Order using Frappe's linked documents cancellation API.
    This properly handles canceling all linked documents (Payment Requests, etc.)
    """
    try:
        # Get the Sales Order
        so = frappe.get_doc("Sales Order", order_id)

        # Verify the order belongs to the current user
        customer = get_customer_from_user()
        if not customer or so.customer != customer:
            return {"success": False, "error": _("You don't have permission to cancel this order")}

        # Check if order is already completed or cancelled
        if so.status in ["Completed", "Cancelled", "Closed"]:
            return {"success": False, "error": _("This order cannot be cancelled")}

        # Check if order is submitted (docstatus = 1)
        if so.docstatus != 1:
            return {"success": False, "error": _("Only submitted orders can be cancelled")}

        # Check if payment has been made
        payment_entries = frappe.get_all("Payment Entry Reference",
            filters={
                "reference_doctype": "Sales Order",
                "reference_name": order_id,
                "docstatus": 1
            },
            fields=["parent"]
        )

        if payment_entries:
            return {"success": False, "error": _("Cannot cancel a paid order. Please contact support.")}

        # First cancel all linked Payment Requests manually
        payment_requests = frappe.get_all(
            "Payment Request",
            filters={
                "reference_doctype": "Sales Order",
                "reference_name": order_id,
                "docstatus": 1  # Only submitted ones
            },
            fields=["name"]
        )
        
        # Cancel each Payment Request individually and commit
        for pr in payment_requests:
            try:
                pr_doc = frappe.get_doc("Payment Request", pr.name)
                if pr_doc.docstatus == 1:
                    pr_doc.cancel()
                    frappe.db.commit()
            except Exception as pr_error:
                frappe.log_error(f"Error cancelling Payment Request {pr.name}: {str(pr_error)}", "Cancel Order Warning")
                # Continue anyway
        
        # Clear cache to ensure links are updated
        frappe.clear_cache()
        
        # Reload Sales Order to get latest state
        so.reload()
        
        # Now cancel the Sales Order itself
        if so.docstatus == 1:  # Only if still submitted
            try:
                so.cancel()
                frappe.db.commit()
            except Exception as cancel_error:
                frappe.log_error(f"Error cancelling Sales Order: {str(cancel_error)}\nTraceback: {frappe.get_traceback()}", "Cancel Order Error")
                # Try one more time after clearing cache
                frappe.clear_cache()
                so.reload()
                if so.docstatus == 1:
                    so.cancel()
                    frappe.db.commit()
        
        # Verify cancellation
        so.reload()
        if so.docstatus != 2:
            frappe.log_error(f"Sales Order {order_id} was not cancelled properly. Docstatus: {so.docstatus}", "Cancel Order Error")
            return {"success": False, "error": _("Order cancellation failed. Please contact support.")}

        return {
            "success": True,
            "message": _("Order cancelled successfully")
        }

    except Exception as e:
        frappe.log_error(f"Error cancelling order: {str(e)}\nOrder: {order_id}\nTraceback: {frappe.get_traceback()}", "Cancel Order Error")
        return {"success": False, "error": _("Failed to cancel order. Please try again or contact support.")}
