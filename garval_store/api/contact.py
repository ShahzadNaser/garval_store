import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def submit(full_name, email, subject, message, phone=None):
    """Submit contact form and send emails"""
    try:
        # Validate required fields
        if not all([full_name, email, subject, message]):
            return {
                "success": False,
                "error": _("Please fill in all required fields")
            }

        # Get admin email using Frappe ORM (frappe.db.get_value)
        # This works for guest users and is version-safe
        admin_email = None
        try:
            # Get default company
            default_company = frappe.db.get_single_value("Global Defaults", "default_company")
            
            if default_company:
                # Try to get company email first
                admin_email = frappe.db.get_value("Company", default_company, "email")
            
            # Fallback to Administrator email if company email not found
            if not admin_email:
                admin_email = frappe.db.get_value("User", "Administrator", "email")
        except Exception as db_error:
            frappe.log_error(f"Failed to get admin email: {str(db_error)}", "Contact Form DB Error")

        # Send notification email to admin
        if admin_email:
            try:
                frappe.sendmail(
                    recipients=[admin_email],
                    subject=f"[Finca Garval] New Contact Form: {subject}",
                    message=f"""
                        <h3>New Contact Form Submission</h3>
                        <p><strong>From:</strong> {full_name} ({email})</p>
                        <p><strong>Phone:</strong> {phone or 'Not provided'}</p>
                        <p><strong>Subject:</strong> {subject}</p>
                        <hr>
                        <p>{message}</p>
                    """,
                    now=True
                )
            except Exception as email_error:
                # Log but don't fail if notification email fails
                frappe.log_error(f"Failed to send admin notification: {str(email_error)}", "Contact Form Email Error")

        # Send confirmation to sender
        try:
            frappe.sendmail(
                recipients=[email],
                subject=_("We received your message - Finca Garval"),
                message=f"""
                    <p>{_('Dear')} {full_name},</p>
                    <p>{_('Thank you for contacting us. We have received your message and will get back to you shortly.')}</p>
                    <p><strong>{_('Your message:')}</strong></p>
                    <blockquote style="background: #f5f5f5; padding: 15px; border-left: 3px solid #33652B;">
                        {message}
                    </blockquote>
                    <p>{_('Best regards,')}<br>Finca Garval</p>
                """,
                now=True
            )
        except Exception as email_error:
            # Log but don't fail if confirmation email fails
            frappe.log_error(f"Failed to send confirmation email: {str(email_error)}", "Contact Form Email Error")

        frappe.db.commit()

        return {
            "success": True,
            "message": _("Message sent successfully")
        }

    except Exception as e:
        error_message = str(e)
        frappe.log_error(f"Contact form error: {error_message}\n{frappe.get_traceback()}", "Contact Form Error")
        frappe.db.rollback()
        return {
            "success": False,
            "error": _("Failed to send message. Please try again."),
            "exc": error_message
        }
