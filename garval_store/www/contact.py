import frappe
from garval_store.utils import set_lang
from frappe.contacts.doctype.address.address import render_address, get_address_display_list
from frappe.contacts.doctype.contact.contact import get_contact_display_list

def get_context(context):
    """Context for contact page"""
    context.lang = set_lang()
    context.no_cache = 1
    
    # Initialize contact info
    context.company_email = None
    context.company_phones = []
    context.company_address_display = None
    
    # Get default company using Frappe ORM
    try:
        default_company = frappe.db.get_single_value("Global Defaults", "default_company")
        # Debug: Log the default company name
        if default_company:
            frappe.logger().debug(f"Contact page - Default company: {default_company}")
    except Exception as e:
        frappe.log_error(f"Error getting default company: {str(e)}", "Contact Page Error")
        default_company = None
    
    if not default_company:
        frappe.log_error("No default company set in Global Defaults", "Contact Page Warning")
        return context
    
    # Get company details using Frappe ORM
    try:
        company_doc = frappe.get_cached_doc("Company", default_company)
        context.company_email = company_doc.get("email")
        if company_doc.get("phone_no"):
            context.company_phones.append(company_doc.get("phone_no"))
    except Exception as e:
        frappe.log_error(f"Error fetching company details: {str(e)}", "Contact Page Error")
    
    # Get phone numbers from contacts linked to company
    try:
        contacts = get_contact_display_list("Company", default_company)
        for contact_info in contacts:
            try:
                contact_doc = frappe.get_cached_doc("Contact", contact_info.get("name"))
                # Get phone numbers from Contact Phone child table
                if hasattr(contact_doc, "phone_nos") and contact_doc.phone_nos:
                    for phone_row in contact_doc.phone_nos:
                        if phone_row.phone and phone_row.phone not in context.company_phones:
                            context.company_phones.append(phone_row.phone)
                # Get mobile number
                if contact_doc.get("mobile_no") and contact_doc.get("mobile_no") not in context.company_phones:
                    context.company_phones.append(contact_doc.get("mobile_no"))
            except Exception as contact_error:
                # Skip individual contact errors, continue with others
                continue
    except Exception as e:
        frappe.log_error(f"Error fetching contact phones: {str(e)}", "Contact Page Error")
    
    # Get company address - use frappe.get_all to bypass permission checks for guest users
    try:
        # Get addresses linked to company using frappe.get_all (works for guest users)
        address_list = frappe.get_all(
            "Address",
            filters=[
                ["Dynamic Link", "link_doctype", "=", "Company"],
                ["Dynamic Link", "link_name", "=", default_company],
                ["Dynamic Link", "parenttype", "=", "Address"],
            ],
            fields=["name", "is_primary_address"],
            order_by="is_primary_address DESC, creation ASC",
            limit=1
        )
        
        if address_list:
            address_name = address_list[0].get("name")
            # Get address document and convert to dict for render_address
            # Using as_dict() to avoid permission issues with document access
            try:
                address_doc = frappe.get_cached_doc("Address", address_name)
                address_dict = address_doc.as_dict()
                # Render address using dict (check_permissions=False allows guest access)
                context.company_address_display = render_address(
                    address_dict, 
                    check_permissions=False
                )
            except Exception as doc_error:
                # If we can't get the doc, try getting all fields directly
                address_dict = frappe.get_all(
                    "Address",
                    filters={"name": address_name},
                    fields=["*"],
                    limit=1
                )
                if address_dict:
                    context.company_address_display = render_address(
                        address_dict[0], 
                        check_permissions=False
                    )
    except Exception as e:
        frappe.log_error(f"Error fetching address: {str(e)}\nDefault Company: {default_company}\nTraceback: {frappe.get_traceback()}", "Contact Page Error")
    
    return context
