# Copyright (c) 2025, Kashif Ali
# License: MIT

import json

import frappe
from frappe import _

from payments.payment_gateways.doctype.stripe_settings.stripe_settings import get_gateway_controller
from garval_store.utils import get_email_verified


@frappe.whitelist()
def process_payment(stripe_token_id, data, reference_doctype=None, reference_docname=None, payment_gateway=None):
    """Process a Stripe payment with the given token"""
    # Require email verification
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to process payment"), frappe.AuthenticationError)
    
    # Check email verification (skip for Administrator)
    if frappe.session.user not in ("Administrator",):
        email_verified = get_email_verified(frappe.session.user)
        if not email_verified:
            frappe.throw(
                _("Please verify your email address before processing payment. Check your inbox for the verification link."),
                frappe.AuthenticationError
            )
    
    data = json.loads(data)
    data.update({"stripe_token_id": stripe_token_id})

    gateway_controller = get_gateway_controller(reference_doctype, reference_docname, payment_gateway)
    data = frappe.get_doc("Stripe Settings", gateway_controller).create_request(data)

    frappe.db.commit()
    return data
