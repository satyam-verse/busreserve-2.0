"""Authentication API blueprint with separated User and Admin portals."""

from flask import Blueprint, g, jsonify, make_response, request

from app.extensions import limiter
from app.models import User
from app.services.auth_service import (
    authenticate_account,
    register_user,
    request_password_reset,
    resend_verification,
    reset_password_with_token,
    revoke_all_user_sessions,
    revoke_session,
    verify_user_email,
)
from app.utils.auth import (
    clear_auth_cookie,
    load_current_auth,
    require_auth,
    set_auth_cookie,
)
from app.utils.errors import ValidationAPIError
from app.utils.schemas import (
    EmailOnlySchema,
    LoginSchema,
    RegisterSchema,
    ResetPasswordSchema,
    VerifyEmailSchema,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_register_schema = RegisterSchema()
_login_schema = LoginSchema()
_verify_schema = VerifyEmailSchema()
_email_only_schema = EmailOnlySchema()
_reset_schema = ResetPasswordSchema()


def _json_body() -> dict:
    raw = request.get_json(silent=True)
    if not isinstance(raw, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")
    return raw


@auth_bp.post("/register")
@limiter.limit("10 per minute")
def register():
    """Register a new passenger account and dispatch verification instructions."""
    data = _register_schema.load(_json_body())
    user, preview = register_user(data)
    payload = {
        "message": "Registration successful. Please verify your email before signing in.",
        "user": user.to_dict(),
    }
    if preview is not None:
        payload["local_mail_preview"] = preview
    return jsonify(payload), 201


@auth_bp.post("/verify-email")
@limiter.limit("10 per minute")
def verify_email():
    """Verify a passenger email address using a single-use token."""
    data = _verify_schema.load(_json_body())
    user = verify_user_email(data["token"])
    return jsonify(
        {
            "message": "Email verified successfully. You may now sign in.",
            "user": user.to_dict(),
        }
    ), 200


@auth_bp.post("/resend-verification")
@limiter.limit("5 per minute")
def resend_verification_email():
    """Re-send verification instructions without leaking account existence."""
    data = _email_only_schema.load(_json_body())
    preview = resend_verification(data["email"])
    payload = {
        "message": (
            "If an unverified account exists for this email, a verification link has been issued."
        )
    }
    if preview is not None:
        payload["local_mail_preview"] = preview
    return jsonify(payload), 200


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def user_login():
    """Authenticate a passenger (USER role only) and issue an HttpOnly session cookie."""
    data = _login_schema.load(_json_body())
    user, session_obj, token, expires_at = authenticate_account(
        email=data["email"],
        password=data["password"],
        required_role=User.ROLE_USER,
    )
    resp = make_response(
        jsonify(
            {
                "message": "Signed in successfully.",
                "user": user.to_dict(),
                "session": session_obj.to_dict(current_jti=session_obj.jti),
            }
        ),
        200,
    )
    set_auth_cookie(resp, token, expires_at)
    return resp


@auth_bp.post("/admin/login")
@limiter.limit("10 per minute")
def admin_login():
    """Separate administrator login endpoint enforcing ADMIN role."""
    data = _login_schema.load(_json_body())
    user, session_obj, token, expires_at = authenticate_account(
        email=data["email"],
        password=data["password"],
        required_role=User.ROLE_ADMIN,
    )
    resp = make_response(
        jsonify(
            {
                "message": "Administrator signed in successfully.",
                "user": user.to_dict(),
                "session": session_obj.to_dict(current_jti=session_obj.jti),
            }
        ),
        200,
    )
    set_auth_cookie(resp, token, expires_at)
    return resp


@auth_bp.post("/forgot-password")
@limiter.limit("5 per minute")
def forgot_password():
    """Initiate a password reset without exposing whether the email is registered."""
    data = _email_only_schema.load(_json_body())
    preview = request_password_reset(data["email"])
    payload = {
        "message": (
            "If an account with that email exists, password reset instructions have been issued."
        )
    }
    if preview is not None:
        payload["local_mail_preview"] = preview
    return jsonify(payload), 200


@auth_bp.post("/reset-password")
@limiter.limit("10 per minute")
def reset_password():
    """Complete password reset and revoke all active sessions for the account."""
    data = _reset_schema.load(_json_body())
    reset_password_with_token(data["token"], data["new_password"])
    resp = make_response(
        jsonify(
            {"message": "Password updated successfully. Please sign in with your new password."}
        ),
        200,
    )
    clear_auth_cookie(resp)
    return resp


@auth_bp.get("/me")
@require_auth
def current_me():
    """Return the authenticated user's profile and active session metadata."""
    return jsonify(
        {
            "user": g.current_user.to_dict(),
            "session": g.current_session.to_dict(current_jti=g.current_session.jti),
        }
    ), 200


@auth_bp.post("/logout")
def logout():
    """Revoke the current server-side session (if present) and clear the auth cookie."""
    _, session_obj = load_current_auth(optional=True)
    if session_obj is not None:
        revoke_session(session_obj)
    resp = make_response(jsonify({"message": "Signed out successfully."}), 200)
    clear_auth_cookie(resp)
    return resp


@auth_bp.post("/logout-all")
@require_auth
def logout_all():
    """Revoke all active sessions for the authenticated user and clear cookie."""
    revoked_count = revoke_all_user_sessions(g.current_user.id)
    resp = make_response(
        jsonify(
            {
                "message": "Signed out from all active sessions.",
                "revoked_sessions": revoked_count,
            }
        ),
        200,
    )
    clear_auth_cookie(resp)
    return resp
