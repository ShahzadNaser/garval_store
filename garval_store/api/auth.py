import frappe
from frappe import _
from frappe.utils import random_string, get_url
from garval_store.utils import create_customer_from_signup


@frappe.whitelist(allow_guest=True)
def login(email, password):
    """Login user and return session info"""
    try:
        from frappe.auth import LoginManager

        # Normalize email - trim whitespace and convert to lowercase
        email = (email or "").strip().lower()

        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        login_manager.post_login()

        # Check if email is verified
        email_verified = frappe.db.get_value("User", frappe.session.user, "email_verified")

        # Ensure Customer role is assigned to user
        user = frappe.get_doc("User", frappe.session.user)
        if "Customer" not in [role.role for role in user.roles]:
            user.add_roles("Customer")
            frappe.db.commit()

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

    except frappe.AuthenticationError:
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

    # Store key in user record
    frappe.db.set_value("User", email, "email_verification_key", verification_key)
    frappe.db.set_value("User", email, "email_verified", 0)
    frappe.db.commit()

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
        stored_key = frappe.db.get_value("User", email, "email_verification_key")

        if not stored_key:
            # Check if already verified
            is_verified = frappe.db.get_value("User", email, "email_verified")
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
        frappe.db.set_value("User", email, "email_verified", 1)
        frappe.db.set_value("User", email, "email_verification_key", None)
        frappe.db.commit()

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
        is_verified = frappe.db.get_value("User", email, "email_verified")
        if is_verified:
            return {
                "success": False,
                "error": _("Email is already verified")
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

    is_verified = frappe.db.get_value("User", frappe.session.user, "email_verified")
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
