import frappe
from frappe import _
from frappe.utils import random_string, get_url
from garval_store.utils import (
    create_customer_from_signup,
    get_email_verified,
    set_email_verified,
    get_email_verification_key,
    set_email_verification_key,
    get_last_verification_email_sent,
    set_last_verification_email_sent
)


@frappe.whitelist(allow_guest=True)
def login(email, password):
    """Login user and return session info"""
    try:
        from frappe.auth import LoginManager

        # Normalize email - trim whitespace and convert to lowercase
        email = (email or "").strip().lower()

        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        
        # Proceed with login
        login_manager.post_login()

        # Ensure Customer role is assigned to user
        user = frappe.get_doc("User", frappe.session.user)

        # Auto-verify email for SSO users
        email_verified = get_email_verified(frappe.session.user)
        real_oauth_providers = ["google", "facebook", "github", "salesforce", "office_365"]
        social_logins = frappe.db.get_all("User Social Login", 
            filters={"parent": frappe.session.user, "provider": ["in", real_oauth_providers]}, 
            fields=["provider"]
        )
        has_social_login = bool(social_logins)
        
        if not email_verified and has_social_login:
            set_email_verified(frappe.session.user, True)
            frappe.db.commit()

        # Create Customer record if not exists (for SSO users)
        try:
            from garval_store.utils import get_customer_from_user
            customer = get_customer_from_user(frappe.session.user)

            if not customer:
                # Get user details
                full_name = user.full_name or user.first_name or frappe.session.user

                # Create Customer
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": full_name,
                    "customer_type": "Individual",
                    "customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual",
                    "territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
                    "email_id": frappe.session.user
                })
                customer.insert(ignore_permissions=True)

                # Add Customer role to user (if not already added)
                if "Customer" not in [r.role for r in user.roles]:
                    user.append("roles", {"role": "Customer"})
                    user.save(ignore_permissions=True)

                # Create Contact and Link
                contact = frappe.get_doc({
                    "doctype": "Contact",
                    "first_name": user.first_name or full_name.split()[0] if full_name else frappe.session.user,
                    "last_name": user.last_name or " ".join(full_name.split()[1:]) if full_name else "",
                    "user": frappe.session.user,
                    "links": [{
                        "link_doctype": "Customer",
                        "link_name": customer.name
                    }]
                })
                contact.append("email_ids", {
                    "email_id": frappe.session.user,
                    "is_primary": 1
                })
                contact.insert(ignore_permissions=True)
                frappe.db.commit()

        except Exception as e:
            frappe.log_error(f"Failed to create customer on login for {frappe.session.user}: {str(e)}\n{frappe.get_traceback()}", "Customer Creation Error")

        # Ensure Stripe Settings permission for Customer role (on first login after deployment)
        try:
            frappe.flags.ignore_permissions = True
            existing_perm = frappe.db.get_value("Custom DocPerm",
                {"parent": "Stripe Settings", "role": "Customer", "read": 1},
                "name"
            )

            if not existing_perm:
                perm_doc = frappe.get_doc({
                    "doctype": "Custom DocPerm",
                    "parent": "Stripe Settings",
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": "Customer",
                    "read": 1,
                    "permlevel": 0
                })
                perm_doc.insert(ignore_permissions=True)
                frappe.db.commit()
                frappe.clear_cache()
        except Exception as perm_error:
            frappe.log_error(f"Failed to setup Stripe permission: {str(perm_error)}", "Login Permission Setup")
        finally:
            frappe.flags.ignore_permissions = False

        return {
            "success": True,
            "user": frappe.session.user,
            "full_name": frappe.db.get_value("User", frappe.session.user, "full_name"),
            "email_verified": bool(email_verified)
        }

    except frappe.AuthenticationError as e:
        # Ensure no session is created on error
        if hasattr(frappe.local, 'session_obj'):
            frappe.local.session_obj = None
        if hasattr(frappe.local, 'session'):
            frappe.local.session = {}
        
        return {
            "success": False,
            "error": _("Invalid email or password")
        }
    except Exception as e:
        frappe.log_error(f"Login error: {str(e)}")
        return {
            "success": False,
            "error": _("Login failed. Please try again.")
        }


@frappe.whitelist(allow_guest=True)
def signup(full_name, email, password, phone=None, newsletter=False):
    """Create new user and customer account with email verification"""
    try:
        # Validate email
        if frappe.db.exists("User", email):
            return {
                "success": False,
                "error": _("An account with this email already exists")
            }

        # Create customer and user
        result = create_customer_from_signup({
            "full_name": full_name,
            "email": email,
            "password": password,
            "phone": phone
        })

        if result.get("success"):
            # Send verification email
            try:
                send_verification_email(email, full_name)
            except Exception as email_error:
                frappe.log_error(f"Failed to send verification email: {str(email_error)}", "Email Verification Error")

            return {
                "success": True,
                "message": _("Account created successfully. Please check your email to verify your account."),
                "requires_verification": True
            }
        else:
            return {
                "success": False,
                "error": result.get("error", _("Failed to create account"))
            }

    except Exception as e:
        frappe.log_error(f"Signup error: {str(e)}")
        return {
            "success": False,
            "error": _("Registration failed. Please try again.")
        }


def send_verification_email(email, full_name):
    """Send email verification link to user"""
    # Generate verification key
    verification_key = random_string(32)

    # Store key in user record and track when email was sent
    from frappe.utils import now
    set_email_verification_key(email, verification_key)
    set_email_verified(email, False)
    # Store timestamp of when verification email was sent (for rate limiting)
    set_last_verification_email_sent(email, now())

    # Build verification URL
    verification_url = get_url(f"/verify-email?key={verification_key}&email={email}")

    # Get current language
    lang = frappe.local.lang or "es"

    if lang == "es":
        subject = "Verifica tu cuenta - Finca Garval"
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #33652B;">Bienvenido a Finca Garval</h2>
            <p>Hola {full_name},</p>
            <p>Gracias por registrarte. Por favor, verifica tu correo electrónico haciendo clic en el siguiente enlace:</p>
            <p style="margin: 30px 0;">
                <a href="{verification_url}" style="background-color: #33652B; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verificar mi cuenta
                </a>
            </p>
            <p>O copia y pega este enlace en tu navegador:</p>
            <p style="color: #666; word-break: break-all;">{verification_url}</p>
            <p>Este enlace expirará en 24 horas.</p>
            <p>Si no has creado esta cuenta, puedes ignorar este correo.</p>
            <br>
            <p>Saludos,<br>El equipo de Finca Garval</p>
        </div>
        """
    else:
        subject = "Verify your account - Finca Garval"
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #33652B;">Welcome to Finca Garval</h2>
            <p>Hello {full_name},</p>
            <p>Thank you for signing up. Please verify your email by clicking the link below:</p>
            <p style="margin: 30px 0;">
                <a href="{verification_url}" style="background-color: #33652B; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify my account
                </a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="color: #666; word-break: break-all;">{verification_url}</p>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create this account, you can ignore this email.</p>
            <br>
            <p>Best regards,<br>The Finca Garval Team</p>
        </div>
        """

    frappe.sendmail(
        recipients=[email],
        subject=subject,
        message=message,
        now=True
    )


@frappe.whitelist(allow_guest=True)
def verify_email(key, email):
    """Verify user email with verification key"""
    try:
        if not key or not email:
            return {
                "success": False,
                "error": _("Invalid verification link")
            }

        # Check if user exists
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "error": _("User not found")
            }

        # Get stored verification key
        stored_key = get_email_verification_key(email)

        if not stored_key:
            # Check if already verified
            is_verified = get_email_verified(email)
            if is_verified:
                return {
                    "success": True,
                    "message": _("Email already verified"),
                    "already_verified": True
                }
            return {
                "success": False,
                "error": _("Invalid or expired verification link")
            }

        if stored_key != key:
            return {
                "success": False,
                "error": _("Invalid verification link")
            }

        # Mark email as verified
        set_email_verified(email, True)
        set_email_verification_key(email, None)

        return {
            "success": True,
            "message": _("Email verified successfully. You can now login.")
        }

    except Exception as e:
        frappe.log_error(f"Email verification error: {str(e)}")
        return {
            "success": False,
            "error": _("Verification failed. Please try again.")
        }


@frappe.whitelist(allow_guest=True)
def resend_verification_email(email):
    """Resend verification email to user"""
    try:
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "error": _("Email not found")
            }

        # Check if already verified
        is_verified = get_email_verified(email)
        if is_verified:
            return {
                "success": False,
                "error": _("Email is already verified")
            }

        # Rate limiting: Check if last email was sent less than 5 minutes ago
        from frappe.utils import now_datetime, get_datetime, add_to_date
        last_sent = get_last_verification_email_sent(email)
        
        if last_sent:
            last_sent_dt = get_datetime(last_sent)
            five_minutes_ago = add_to_date(now_datetime(), minutes=-5)
            
            if last_sent_dt > five_minutes_ago:
                # Calculate remaining time
                remaining_seconds = (last_sent_dt - five_minutes_ago).total_seconds()
                remaining_minutes = int(remaining_seconds / 60) + 1  # Round up
                
                lang = frappe.local.lang or "es"
                if lang == "es":
                    error_msg = _("Por favor espera {0} minutos antes de solicitar otro correo de verificación.").format(remaining_minutes)
                else:
                    error_msg = _("Please wait {0} minutes before requesting another verification email.").format(remaining_minutes)
                
                return {
                    "success": False,
                    "error": error_msg,
                    "wait_time_minutes": remaining_minutes
                }

        # Get user's full name
        full_name = frappe.db.get_value("User", email, "full_name") or email

        # Send new verification email
        send_verification_email(email, full_name)

        return {
            "success": True,
            "message": _("Verification email sent. Please check your inbox.")
        }

    except Exception as e:
        frappe.log_error(f"Resend verification error: {str(e)}")
        return {
            "success": False,
            "error": _("Failed to send verification email. Please try again.")
        }


@frappe.whitelist()
def check_email_verified():
    """Check if current user's email is verified"""
    if frappe.session.user == "Guest":
        return {"verified": False, "is_guest": True}

    is_verified = get_email_verified(frappe.session.user)
    return {
        "verified": bool(is_verified),
        "is_guest": False
    }


@frappe.whitelist()
def update_profile(full_name, phone=None):
    """Update user profile"""
    try:
        user = frappe.session.user
        if user == "Guest":
            return {"success": False, "error": _("Not logged in")}

        # Update User
        frappe.db.set_value("User", user, "full_name", full_name)

        # Update Customer if exists
        from garval_store.utils import get_customer_from_user
        customer = get_customer_from_user()
        if customer:
            frappe.db.set_value("Customer", customer, "customer_name", full_name)
            if phone:
                frappe.db.set_value("Customer", customer, "mobile_no", phone)

        frappe.db.commit()

        return {
            "success": True,
            "message": _("Profile updated successfully")
        }

    except Exception as e:
        frappe.log_error(f"Update profile error: {str(e)}")
        return {
            "success": False,
            "error": _("Failed to update profile")
        }


@frappe.whitelist()
def change_password(current_password, new_password):
    """Change user password"""
    try:
        from frappe.utils.password import check_password, update_password

        user = frappe.session.user
        if user == "Guest":
            return {"success": False, "error": _("Not logged in")}

        # Verify current password
        try:
            check_password(user, current_password)
        except frappe.AuthenticationError:
            return {
                "success": False,
                "error": _("Current password is incorrect")
            }

        # Update password
        update_password(user, new_password)
        frappe.db.commit()

        return {
            "success": True,
            "message": _("Password changed successfully")
        }

    except Exception as e:
        frappe.log_error(f"Change password error: {str(e)}")
        return {
            "success": False,
            "error": _("Failed to change password")
        }


@frappe.whitelist()
def logout():
    """Logout current user"""
    try:
        from frappe.auth import LoginManager
        login_manager = LoginManager()
        login_manager.logout()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
