import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add last_verification_email_sent custom field to User doctype"""
	
	if not frappe.db.exists("DocType", "User"):
		return
	
	# Check if field already exists
	if frappe.db.exists("Custom Field", {"fieldname": "last_verification_email_sent", "dt": "User"}):
		return
	
	custom_fields = {
		"User": [
            dict(
                fieldname="email_verified",
                label="Email Verified",
                fieldtype="Check",
                insert_after="enabled",
                default="0",
                read_only=1,
                description="Checked when user verifies their email address"
            ),
            dict(
                fieldname="email_verification_key",
                label="Email Verification Key",
                fieldtype="Data",
                insert_after="email_verified",
                hidden=1,
                read_only=1,
                description="Temporary key for email verification"
            ),
            dict(
                fieldname="last_verification_email_sent",
                label="Last Verification Email Sent",
                fieldtype="Datetime",
                insert_after="email_verification_key",
                hidden=1,
                read_only=1,
                description="Timestamp of when the last verification email was sent (for rate limiting)"
            ),
        ],
	}
	
	create_custom_fields(custom_fields, ignore_validate=True, update=True)
	
	# Ensure database schema is updated
	frappe.clear_cache(doctype="User")
	frappe.db.updatedb("User")
	frappe.db.commit()
	print("Created Custom Field: User-last_verification_email_sent")

