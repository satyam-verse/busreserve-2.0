"""JWT authentication, HttpOnly cookie transport, session validation, and RBAC decorators."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from functools import wraps

import jwt
from flask import current_app, g, request
from sqlalchemy import select

from app.extensions import db
from app.models import AuthSession, User
from app.utils.errors import ForbiddenError, UnauthorizedError


def hash_token(raw_token: str) -> str:
    """Return hex SHA-256 digest for single-use verification/reset tokens."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_secure_token() -> str:
    """Generate a URL-safe cryptographic token."""
    return secrets.token_urlsafe(32)


def issue_access_token(user: User, session_jti: str, expires_at: datetime) -> str:
    """Encode a signed HS256 JWT carrying user ID, role, and DB session jti."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "jti": session_jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )


def set_auth_cookie(response, token: str, expires_at: datetime) -> None:
    """Attach the JWT inside an HttpOnly SameSite cookie."""
    max_age = max(60, int((expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        current_app.config["JWT_COOKIE_NAME"],
        value=token,
        max_age=max_age,
        expires=expires_at,
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite=current_app.config["COOKIE_SAMESITE"],
        path="/",
    )


def clear_auth_cookie(response) -> None:
    """Expire and remove the authentication cookie on logout."""
    response.delete_cookie(
        current_app.config["JWT_COOKIE_NAME"],
        path="/",
        httponly=True,
        secure=current_app.config["COOKIE_SECURE"],
        samesite=current_app.config["COOKIE_SAMESITE"],
    )


def _extract_raw_token() -> str | None:
    cookie_name = current_app.config["JWT_COOKIE_NAME"]
    cookie_token = request.cookies.get(cookie_name)
    if cookie_token:
        return cookie_token.strip()

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def load_current_auth(optional: bool = False) -> tuple[User | None, AuthSession | None]:
    """Validate incoming JWT against DB AuthSession and User status."""
    raw_token = _extract_raw_token()
    if not raw_token:
        if optional:
            g.current_user = None
            g.current_session = None
            return None, None
        raise UnauthorizedError("Authentication is required.")

    try:
        decoded = jwt.decode(
            raw_token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError as exc:
        if optional:
            g.current_user = None
            g.current_session = None
            return None, None
        raise UnauthorizedError("Your session has expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        if optional:
            g.current_user = None
            g.current_session = None
            return None, None
        raise UnauthorizedError("Invalid authentication token.") from exc

    jti = decoded.get("jti")
    sub = decoded.get("sub")
    if not jti or not sub:
        if optional:
            g.current_user = None
            g.current_session = None
            return None, None
        raise UnauthorizedError("Malformed authentication token.")

    session_obj = db.session.execute(
        select(AuthSession).where(AuthSession.jti == jti)
    ).scalar_one_or_none()
    if session_obj is None or not session_obj.is_valid():
        if optional:
            g.current_user = None
            g.current_session = None
            return None, None
        raise UnauthorizedError("Session is no longer active. Please sign in again.")

    user = session_obj.user
    if user is None or not user.is_active or str(user.id) != str(sub):
        if optional:
            g.current_user = None
            g.current_session = None
            return None, None
        raise UnauthorizedError("Account is inactive or unavailable.")

    g.current_user = user
    g.current_session = session_obj
    return user, session_obj


def require_auth(fn):
    """Decorator enforcing an active authenticated user or admin session."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        load_current_auth(optional=False)
        return fn(*args, **kwargs)

    return wrapper


def require_role(*allowed_roles: str):
    """Decorator enforcing role-based access control on backend endpoints."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user, _ = load_current_auth(optional=False)
            if user is None or user.role not in allowed_roles:
                raise ForbiddenError("You do not have permission to access this resource.")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_admin(fn):
    """Decorator restricting access strictly to authenticated ADMIN accounts."""
    return require_role(User.ROLE_ADMIN)(fn)


require_roles = require_role


def require_driver(fn):
    """Decorator restricting access to authenticated DRIVER or ADMIN accounts."""
    return require_role(User.ROLE_DRIVER, User.ROLE_ADMIN)(fn)


def require_operator(fn):
    """Decorator restricting access to authenticated OPERATOR or ADMIN accounts."""
    return require_role(User.ROLE_OPERATOR, User.ROLE_ADMIN)(fn)


def create_user_session(user: User) -> tuple[AuthSession, str, datetime]:
    """Create a persistent DB AuthSession and return (session, jwt_token, expires_at)."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=current_app.config["JWT_ACCESS_TOKEN_EXPIRES_MINUTES"])
    jti = secrets.token_hex(24)

    forwarded_for = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    ip_addr = (forwarded_for or request.remote_addr or "")[:64] or None
    user_agent = (request.headers.get("User-Agent") or "")[:255] or None

    session_obj = AuthSession(
        jti=jti,
        user_id=user.id,
        role=user.role,
        ip_address=ip_addr,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.session.add(session_obj)
    db.session.flush()

    token = issue_access_token(user, jti, expires_at)
    return session_obj, token, expires_at


def ai_rate_limit_key() -> str:
    """Rate-limit AI endpoints per authenticated user ID when available, else client IP."""
    raw_token = _extract_raw_token()
    if raw_token:
        try:
            decoded = jwt.decode(
                raw_token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
            )
            sub = decoded.get("sub")
            if sub:
                return f"ai:user:{sub}"
        except jwt.PyJWTError:
            pass
    forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    return f"ai:ip:{forwarded or request.remote_addr or 'unknown'}"
