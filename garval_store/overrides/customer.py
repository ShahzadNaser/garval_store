import frappe
from erpnext.selling.doctype.customer.customer import Customer as OriginalCustomer, make_contact


class Customer(OriginalCustomer):
	def create_primary_contact(self):
		"""Override to handle permission errors when updating Contact during OAuth login"""
		if not self.customer_primary_contact and not self.lead_name:
			if self.mobile_no or self.email_id or self.first_name or self.last_name:
				contact = make_contact(self)
				self.db_set("customer_primary_contact", contact.name)
				self.db_set("mobile_no", self.mobile_no)
				self.db_set("email_id", self.email_id)
		elif self.customer_primary_contact:
			# Get the Contact document and save with ignore_permissions to avoid permission errors
			# This is especially important during OAuth login when user permissions may not be fully set
			# Always use ignore_permissions=True since this is a system operation that should always succeed
			try:
				contact = frappe.get_doc("Contact", self.customer_primary_contact)
				contact.is_primary_contact = 1
				contact.flags.ignore_permissions = True
				contact.save(ignore_permissions=True)
			except frappe.DoesNotExistError:
				# Contact doesn't exist, skip
				pass

