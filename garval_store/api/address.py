import frappe
from garval_store.utils import get_customer_from_user


@frappe.whitelist()
def get_address(address_id):
    """Get address details"""
    try:
        # Verify user owns this address
        customer_name = get_customer_from_user()
        if not customer_name:
            return {"success": False, "error": "Not logged in"}

        address = frappe.get_doc("Address", address_id)

        # Check if address belongs to customer
        is_customer_address = False
        for link in address.links:
            if link.link_doctype == "Customer" and link.link_name == customer_name:
                is_customer_address = True
                break

        if not is_customer_address:
            return {"success": False, "error": "Unauthorized"}

        return {
            "success": True,
            "address": {
                "name": address.name,
                "address_title": address.address_title or "",
                "address_line1": address.address_line1 or "",
                "address_line2": address.address_line2 or "",
                "city": address.city or "",
                "state": address.state or "",
                "pincode": address.pincode or "",
                "country": address.country or "",
                "phone": address.phone or ""
            }
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Address Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def create_address(address_title, address_line1, address_line2, city, state, pincode, country, phone=None):
    """Create a new address for the customer"""
    try:
        customer_name = get_customer_from_user()
        if not customer_name:
            return {"success": False, "error": "Not logged in"}

        # Create new address
        address = frappe.get_doc({
            "doctype": "Address",
            "address_title": address_title,
            "address_line1": address_line1,
            "address_line2": address_line2,
            "city": city,
            "state": state,
            "pincode": pincode,
            "country": country,
            "phone": phone,
            "links": [
                {
                    "link_doctype": "Customer",
                    "link_name": customer_name
                }
            ]
        })
        address.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "address_id": address.name,
            "message": "Address created successfully"
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Address Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def update_address(address_id, address_title, address_line1, address_line2, city, state, pincode, country, phone=None):
    """Update an existing address"""
    try:
        customer_name = get_customer_from_user()
        if not customer_name:
            return {"success": False, "error": "Not logged in"}

        address = frappe.get_doc("Address", address_id)

        # Check if address belongs to customer
        is_customer_address = False
        for link in address.links:
            if link.link_doctype == "Customer" and link.link_name == customer_name:
                is_customer_address = True
                break

        if not is_customer_address:
            return {"success": False, "error": "Unauthorized"}

        # Update address fields
        address.address_title = address_title
        address.address_line1 = address_line1
        address.address_line2 = address_line2
        address.city = city
        address.state = state
        address.pincode = pincode
        address.country = country
        address.phone = phone

        address.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Address updated successfully"
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update Address Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def delete_address(address_id):
    """Delete an address"""
    try:
        customer_name = get_customer_from_user()
        if not customer_name:
            return {"success": False, "error": "Not logged in"}

        address = frappe.get_doc("Address", address_id)

        # Check if address belongs to customer
        is_customer_address = False
        for link in address.links:
            if link.link_doctype == "Customer" and link.link_name == customer_name:
                is_customer_address = True
                break

        if not is_customer_address:
            return {"success": False, "error": "Unauthorized"}

        # Delete the address (force=1 to bypass validation)
        frappe.delete_doc("Address", address_id, ignore_permissions=True, force=1)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Address deleted successfully"
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Delete Address Error")
        return {"success": False, "error": str(e)}
