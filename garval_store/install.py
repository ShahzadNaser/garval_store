import frappe


def after_install():
    """Setup custom fields and permissions after app installation"""
    create_email_verification_fields()
    setup_customer_role_permissions()
    frappe.db.commit()


def create_email_verification_fields():
    """Create custom fields on User doctype for email verification"""

    # Check if email_verified field exists
    if not frappe.db.exists("Custom Field", "User-email_verified"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "User",
            "fieldname": "email_verified",
            "fieldtype": "Check",
            "label": "Email Verified",
            "insert_after": "enabled",
            "default": "0",
            "read_only": 1,
            "description": "Checked when user verifies their email address"
        }).insert(ignore_permissions=True)
        print("Created Custom Field: User-email_verified")

    # Check if email_verification_key field exists
    if not frappe.db.exists("Custom Field", "User-email_verification_key"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "User",
            "fieldname": "email_verification_key",
            "fieldtype": "Data",
            "label": "Email Verification Key",
            "insert_after": "email_verified",
            "hidden": 1,
            "read_only": 1,
            "description": "Temporary key for email verification"
        }).insert(ignore_permissions=True)
        print("Created Custom Field: User-email_verification_key")


def setup_customer_role_permissions():
    """Setup permissions for Customer role to access webshop functionality"""

    # DocTypes with read-only access
    doctypes_read_only = [
        "User",
        "Item",
        "Item Group",
        "Website Item",
        "Item Price",
        "Price List",
        "Account",
        "Payment Gateway Account",
        "Portal Settings",
        "Webshop Settings",
        "Territory",
        "Customer Group",
        "Company",
        "Currency",
        "Sales Taxes and Charges Template",
        "Shipping Rule",
        "Payment Entry",
        "Sales Order",
        "Sales Invoice",
    ]

    # DocTypes with read/write access (own records only)
    doctypes_read_write = [
        "Customer",
        "Contact",
    ]

    # DocTypes with read/write/create access
    doctypes_read_write_create = [
        "Address",
        "Quotation",
    ]

    role = "Customer"

    # Ensure Customer role exists
    if not frappe.db.exists("Role", role):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role,
            "desk_access": 0,
            "is_custom": 1
        }).insert(ignore_permissions=True)
        print(f"Created Role: {role}")

    # Add read-only permissions
    for dt in doctypes_read_only:
        add_permission(dt, role, read=1)

    # Add read/write permissions
    for dt in doctypes_read_write:
        add_permission(dt, role, read=1, write=1)

    # Add read/write/create permissions
    for dt in doctypes_read_write_create:
        add_permission(dt, role, read=1, write=1, create=1)

    print("Customer role permissions setup completed")


def add_permission(doctype, role, read=0, write=0, create=0, delete=0, submit=0, cancel=0):
    """Add permission for a role on a doctype if it doesn't exist"""

    # Check if DocType exists
    if not frappe.db.exists("DocType", doctype):
        print(f"DocType {doctype} does not exist, skipping permission")
        return

    # Check if permission already exists
    existing = frappe.db.exists("Custom DocPerm", {
        "parent": doctype,
        "role": role,
        "permlevel": 0
    })

    if existing:
        # Update existing permission
        frappe.db.set_value("Custom DocPerm", existing, {
            "read": read,
            "write": write,
            "create": create,
            "delete": delete,
            "submit": submit,
            "cancel": cancel
        })
        print(f"Updated permission for {role} on {doctype}")
    else:
        # Create new permission
        frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": doctype,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": role,
            "permlevel": 0,
            "read": read,
            "write": write,
            "create": create,
            "delete": delete,
            "submit": submit,
            "cancel": cancel
        }).insert(ignore_permissions=True)
        print(f"Added permission for {role} on {doctype}")
