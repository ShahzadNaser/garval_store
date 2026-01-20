# Copyright (c) 2025, Kashif Ali
# License: MIT

import frappe
from frappe import _
from frappe.utils import fmt_money

from payments.payment_gateways.doctype.stripe_settings.stripe_settings import get_gateway_controller

no_cache = 1

expected_keys = (
    "amount",
    "title",
    "description",
    "reference_doctype",
    "reference_docname",
    "payer_name",
    "payer_email",
    "currency",
    "payment_gateway",
)


def get_context(context):
    context.no_cache = 1

    # Check if user is logged in, if not redirect to customer login
    if frappe.session.user == "Guest":
        from urllib.parse import quote
        redirect_url = frappe.request.path + "?" + frappe.request.query_string.decode()
        frappe.local.flags.redirect_location = "/customer-login?redirect-to=" + quote(redirect_url)
        raise frappe.Redirect

    # Validate all required keys are present
    if not (set(expected_keys) - set(list(frappe.form_dict))):
        for key in expected_keys:
            context[key] = frappe.form_dict[key]

        gateway_controller = get_gateway_controller(
            context.reference_doctype, context.reference_docname, context.payment_gateway
        )
        context.publishable_key = get_api_key(context.reference_docname, gateway_controller)
        context["amount"] = fmt_money(amount=context["amount"], currency=context["currency"])

    else:
        frappe.redirect_to_message(
            _("Invalid Request"),
            _("Required payment information is missing. Please contact support."),
        )
        frappe.local.flags.redirect_location = frappe.local.response.location
        raise frappe.Redirect


def get_api_key(doc, gateway_controller):
    from frappe.utils import cint
    publishable_key = frappe.db.get_value("Stripe Settings", gateway_controller, "publishable_key")
    if cint(frappe.form_dict.get("use_sandbox")):
        publishable_key = frappe.conf.sandbox_publishable_key
    return publishable_key
