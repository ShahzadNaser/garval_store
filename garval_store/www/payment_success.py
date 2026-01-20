# Copyright (c) 2025, Kashif Ali
# License: MIT

import frappe

no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.payment_message = frappe.form_dict.get("redirect_message")
    context.redirect_to = frappe.form_dict.get("redirect_to") or "/my-account#orders"
