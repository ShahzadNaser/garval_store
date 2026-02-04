# Copyright (c) Garval Store
# Redirect payment success "My Account" to /my-account instead of /me

from webshop.webshop.doctype.override_doctype.payment_request import (
	PaymentRequest as WebshopPaymentRequest,
)


class PaymentRequest(WebshopPaymentRequest):
	def on_payment_authorized(self, status=None):
		super().on_payment_authorized(status)
		# Use /my-account for "My Account" (garval_store route)
		
		return "/my-account"
