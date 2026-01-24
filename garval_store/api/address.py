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

        # Handle URL-encoded address_id and get from form_dict if not provided
        if not address_id:
            address_id = frappe.form_dict.get('address_id')
        
        if not address_id:
            return {"success": False, "error": "Address ID is required"}

        # Check if address exists
        if not frappe.db.exists("Address", address_id):
            return {"success": False, "error": f"Address {address_id} not found"}

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
def update_address(address_id=None, address_title=None, address_line1=None, address_line2=None, city=None, state=None, pincode=None, country=None, phone=None):
    """Update an existing address"""
    try:
        # Get data from form_dict (handles both form and JSON)
        data = frappe.form_dict
        
        # Extract address_id - check both parameter and form_dict
        address_id = address_id or data.get('address_id') or data.get('name')
        
        if not address_id:
            return {"success": False, "error": "Address ID is required"}
        
        # Get other fields from form_dict if not provided as parameters
        address_title = address_title or data.get('address_title')
        address_line1 = address_line1 or data.get('address_line1')
        address_line2 = address_line2 or data.get('address_line2')
        city = city or data.get('city')
        state = state or data.get('state')
        pincode = pincode or data.get('pincode')
        country = country or data.get('country')
        phone = phone or data.get('phone')
        
        customer_name = get_customer_from_user()
        if not customer_name:
            return {"success": False, "error": "Not logged in"}

        if not frappe.db.exists("Address", address_id):
            return {"success": False, "error": "Address not found"}

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
