# Copyright (c) 2025, Kashif Ali
# License: MIT

import json

import frappe

from payments.payment_gateways.doctype.stripe_settings.stripe_settings import get_gateway_controller


@frappe.whitelist()
def process_payment(stripe_token_id, data, reference_doctype=None, reference_docname=None, payment_gateway=None):
    """Process a Stripe payment with the given token"""
    data = json.loads(data)
    data.update({"stripe_token_id": stripe_token_id})

    gateway_controller = get_gateway_controller(reference_doctype, reference_docname, payment_gateway)
    data = frappe.get_doc("Stripe Settings", gateway_controller).create_request(data)

    frappe.db.commit()
    return data
