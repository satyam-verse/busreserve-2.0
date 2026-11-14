"""Comprehensive tests for User auth, Admin RBAC, sessions, ownership, and rate limiting."""

import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app import create_app
from app.extensions import db, limiter
from app.models import AuthSession, User
from scripts.seed import run_seed

ADMIN_TEST_PW = os.getenv("SEED_DEMO_ADMIN_PASSWORD", "TestAdminPass999!")
USER_TEST_PW = os.getenv("SEED_DEMO_USER_PASSWORD", "TestUserPass999!")


def _create_verified_user(client, email="user1@example.com", password="UserPass@123"):
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "Neha Kapoor",
            "email": email,
            "phone": "9876543210",
            "password": password,
        },
    )
    assert reg.status_code == 201
    data = reg.get_json()
    assert "password_hash" not in str(data)
    token = data["local_mail_preview"]["token"]

    # Login before verification must fail (403 email_not_verified)
    pre_verify = client.post("/api/auth/login", json={"email": email, "password": password})
    assert pre_verify.status_code == 403
    assert pre_verify.get_json()["error"]["code"] == "email_not_verified"

    verify = client.post("/api/auth/verify-email", json={"token": token})
    assert verify.status_code == 200

    # Single-use token cannot be reused
    reuse = client.post("/api/auth/verify-email", json={"token": token})
    assert reuse.status_code == 400
    return data["user"]


def test_user_registration_verification_login_profile_and_logout(client, app):
    # Weak password rejected
    weak = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test User",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert weak.status_code == 400

    _create_verified_user(client, email="neha@example.com", password="UserPass@123")

    # Duplicate email returns 409
    dup = client.post(
        "/api/auth/register",
        json={
            "full_name": "Neha Duplicate",
            "email": "neha@example.com",
            "password": "UserPass@123",
        },
    )
    assert dup.status_code == 409

    # Login sets HttpOnly cookie and never exposes password_hash
    login = client.post(
        "/api/auth/login",
        json={"email": "neha@example.com", "password": "UserPass@123"},
    )
    assert login.status_code == 200
    set_cookie = login.headers.get("Set-Cookie", "")
    assert "HttpOnly" in set_cookie
    assert "password_hash" not in login.get_data(as_text=True)

    # /api/auth/me and profile update work with cookie
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "neha@example.com"

    upd = client.patch(
        "/api/user/profile",
        json={"full_name": "Neha Kapoor Sharma", "phone": "9876543299"},
    )
    assert upd.status_code == 200
    assert upd.get_json()["user"]["full_name"] == "Neha Kapoor Sharma"

    sessions = client.get("/api/user/sessions")
    assert sessions.status_code == 200
    assert sessions.get_json()["count"] == 1
    assert sessions.get_json()["sessions"][0]["is_current"] is True

    # Logout revokes DB session and subsequent /api/auth/me returns 401
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_forgot_and_reset_password_revokes_active_sessions_and_hides_tokens_when_disabled(
    client, app
):
    _create_verified_user(client, email="reset@example.com", password="OldPass@123")
    assert (
        client.post(
            "/api/auth/login", json={"email": "reset@example.com", "password": "OldPass@123"}
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me").status_code == 200

    # With local mail preview off, no token leaks in JSON and enumeration is prevented
    app.config["ALLOW_LOCAL_MAIL_PREVIEW"] = False
    try:
        non_existent = client.post(
            "/api/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        assert non_existent.status_code == 200
        assert "local_mail_preview" not in non_existent.get_json()

        hidden = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
        assert hidden.status_code == 200
        assert "local_mail_preview" not in hidden.get_json()
    finally:
        app.config["ALLOW_LOCAL_MAIL_PREVIEW"] = True

    forgot = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert forgot.status_code == 200
    reset_token = forgot.get_json()["local_mail_preview"]["token"]

    reset = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "NewPass@456"},
    )
    assert reset.status_code == 200

    # Prior session was revoked server-side on reset
    assert client.get("/api/auth/me").status_code == 401
    # Old password no longer works; new password works
    assert (
        client.post(
            "/api/auth/login", json={"email": "reset@example.com", "password": "OldPass@123"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "reset@example.com", "password": "NewPass@456"}
        ).status_code
        == 200
    )

    # Admin accounts must never issue self-service password reset tokens on public forgot-password
    with app.app_context():
        run_seed(horizon_days=1)
    admin_forgot = client.post(
        "/api/auth/forgot-password", json={"email": "admin@busreserve.local"}
    )
    assert admin_forgot.status_code == 200
    assert "local_mail_preview" not in admin_forgot.get_json()
    with app.app_context():
        adm = db.session.execute(
            select(User).where(User.email == "admin@busreserve.local")
        ).scalar_one()
        assert adm.password_reset_token_hash is None

    # Production config defaults fail closed when mail preview / cookie env vars are omitted
    try:
        prod_app = create_app(
            "production",
            config_overrides={"SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"]},
        )
        assert prod_app.config["COOKIE_SECURE"] is True
        assert prod_app.config["ALLOW_LOCAL_MAIL_PREVIEW"] is False
    finally:
        limiter.reset()
        limiter.init_app(app)


def test_expired_email_and_reset_tokens_rejected(client, app):
    _create_verified_user(client, email="exp@example.com", password="ValidPass@123")
    forgot = client.post("/api/auth/forgot-password", json={"email": "exp@example.com"})
    token = forgot.get_json()["local_mail_preview"]["token"]

    with app.app_context():
        user = db.session.execute(select(User).where(User.email == "exp@example.com")).scalar_one()
        user.password_reset_expires_at = datetime.now(UTC) - timedelta(minutes=5)
        db.session.commit()

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "AnotherPass@789"},
    )
    assert resp.status_code == 400


def test_user_booking_ownership_isolation_and_my_bookings(client, app, sample_data):
    client_a = app.test_client()
    client_b = app.test_client()

    _create_verified_user(client_a, email="ownera@example.com", password="UserPass@123")
    _create_verified_user(client_b, email="ownerb@example.com", password="UserPass@123")

    assert (
        client_a.post(
            "/api/auth/login", json={"email": "ownera@example.com", "password": "UserPass@123"}
        ).status_code
        == 200
    )
    assert (
        client_b.post(
            "/api/auth/login", json={"email": "ownerb@example.com", "password": "UserPass@123"}
        ).status_code
        == 200
    )

    book = client_a.post(
        "/api/bookings",
        json={
            "trip_id": sample_data["upcoming_trip_id"],
            "seat_number": "1B",
            "passenger_name": "Neha Kapoor",
            "passenger_email": "ownera@example.com",
            "passenger_phone": "9876543210",
            "boarding_stop_id": sample_data["pr_stop_ids"][0],
            "drop_stop_id": sample_data["pr_stop_ids"][3],
        },
    )
    assert book.status_code == 201
    pnr = book.get_json()["booking"]["pnr"]

    # Owner A sees it in My Bookings
    my_a = client_a.get("/api/user/bookings")
    assert my_a.status_code == 200
    assert my_a.get_json()["count"] == 1
    assert my_a.get_json()["bookings"][0]["pnr"] == pnr

    # Unauthenticated and User B cannot read or cancel User A's booking
    assert client.get(f"/api/bookings/{pnr}").status_code == 401
    assert client.post(f"/api/bookings/{pnr}/cancel").status_code == 401
    assert client_b.get(f"/api/bookings/{pnr}").status_code == 403
    assert client_b.post(f"/api/user/bookings/{pnr}/cancel").status_code == 403
    assert client_b.get("/api/user/bookings").get_json()["count"] == 0

    # Owner A cancels via /api/user/bookings/<pnr>/cancel
    cancel_a = client_a.post(f"/api/user/bookings/{pnr}/cancel")
    assert cancel_a.status_code == 200
    assert cancel_a.get_json()["booking"]["status"] == "CANCELLED"


def test_role_separation_and_protected_admin_crud_workflows(client, app):
    with app.app_context():
        run_seed(horizon_days=5)

    user_client = app.test_client()
    admin_client = app.test_client()

    # Portal separation: ADMIN rejected on user login; USER rejected on admin login
    assert (
        user_client.post(
            "/api/auth/login",
            json={"email": "admin@busreserve.local", "password": ADMIN_TEST_PW},
        ).status_code
        == 403
    )
    assert (
        admin_client.post(
            "/api/auth/admin/login",
            json={"email": "passenger@busreserve.local", "password": USER_TEST_PW},
        ).status_code
        == 403
    )

    # Login user properly and verify all /api/admin/* endpoints reject USER with 403
    assert (
        user_client.post(
            "/api/auth/login",
            json={"email": "passenger@busreserve.local", "password": USER_TEST_PW},
        ).status_code
        == 200
    )
    for method, path, body in [
        ("GET", "/api/admin/overview", None),
        ("GET", "/api/admin/users", None),
        ("GET", "/api/admin/bookings", None),
        ("POST", "/api/admin/cities", {"name": "Kota", "state": "Rajasthan"}),
        (
            "POST",
            "/api/admin/routes",
            {"name": "X to Y", "source": "X", "destination": "Y", "stops": ["X", "Y"]},
        ),
    ]:
        # Unauthenticated gets 401
        assert getattr(client, method.lower())(path, json=body).status_code == 401
        # Regular USER gets 403
        assert getattr(user_client, method.lower())(path, json=body).status_code == 403

    # Authenticate ADMIN on separate admin login endpoint
    admin_login = admin_client.post(
        "/api/auth/admin/login",
        json={"email": "admin@busreserve.local", "password": ADMIN_TEST_PW},
    )
    assert admin_login.status_code == 200
    assert admin_login.get_json()["user"]["role"] == "ADMIN"

    # Admin user management: list users, suspend demo user -> active user session invalidated
    users_resp = admin_client.get("/api/admin/users")
    assert users_resp.status_code == 200
    passenger_user = next(
        u for u in users_resp.get_json()["users"] if u["email"] == "passenger@busreserve.local"
    )
    admin_user = next(
        u for u in users_resp.get_json()["users"] if u["email"] == "admin@busreserve.local"
    )

    # Admin cannot deactivate self
    assert (
        admin_client.patch(
            f"/api/admin/users/{admin_user['id']}", json={"is_active": False}
        ).status_code
        == 409
    )

    # Suspending regular user revokes their active session immediately
    suspend = admin_client.patch(
        f"/api/admin/users/{passenger_user['id']}", json={"is_active": False}
    )
    assert suspend.status_code == 200
    assert user_client.get("/api/auth/me").status_code == 401

    # Reactivate user
    assert (
        admin_client.patch(
            f"/api/admin/users/{passenger_user['id']}", json={"is_active": True}
        ).status_code
        == 200
    )

    # Admin booking management: view & cancel seeded booking BRSEED0001
    bookings_resp = admin_client.get("/api/admin/bookings?q=BRSEED0001")
    assert bookings_resp.status_code == 200
    assert bookings_resp.get_json()["count"] == 1
    assert admin_client.post("/api/admin/bookings/BRSEED0001/cancel").status_code == 200

    # Admin protected CRUD: create city, route, schedule -> immediately searchable publicly
    assert (
        admin_client.post(
            "/api/admin/cities", json={"name": "Udaipur", "state": "Rajasthan", "aliases": "UDR"}
        ).status_code
        == 201
    )
    assert (
        admin_client.post(
            "/api/admin/cities", json={"name": "Jodhpur", "state": "Rajasthan", "aliases": "JDH"}
        ).status_code
        == 201
    )
    route_resp = admin_client.post(
        "/api/admin/routes",
        json={
            "name": "Udaipur to Jodhpur Desert Express",
            "source": "Udaipur",
            "destination": "Jodhpur",
            "stops": ["Udaipur (Udiapole)", "Pali", "Jodhpur (Raika Bagh)"],
        },
    )
    assert route_resp.status_code == 201
    new_route_id = route_resp.get_json()["route"]["id"]

    sched_resp = admin_client.post(
        "/api/admin/schedules",
        json={
            "route_id": new_route_id,
            "operator_name": "Mewar Heritage Coach",
            "bus_number": "RJ-27-PA-9901",
            "departure_time": "09:00",
            "arrival_time": "14:00",
            "base_fare": 590,
            "seat_count": 20,
        },
    )
    assert sched_resp.status_code == 201

    public_search = client.get("/api/trips?source=Udaipur&destination=Jodhpur")
    assert public_search.status_code == 200
    assert public_search.get_json()["count"] >= 1

    # Admin logout invalidates admin session
    assert admin_client.post("/api/auth/logout").status_code == 200
    assert admin_client.get("/api/admin/overview").status_code == 401

    with app.app_context():
        active_admin_sessions = (
            db.session.execute(
                select(AuthSession).where(
                    AuthSession.user_id == admin_user["id"],
                    AuthSession.revoked_at.is_(None),
                )
            )
            .scalars()
            .all()
        )
        assert active_admin_sessions == []


def test_auth_rate_limiting_enforced_when_enabled(app):
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    rl_app = create_app(
        "testing",
        config_overrides={
            "SQLALCHEMY_DATABASE_URI": db_uri,
            "RATELIMIT_ENABLED": True,
        },
    )
    rl_client = rl_app.test_client()

    try:
        statuses = []
        for idx in range(12):
            resp = rl_client.post(
                "/api/auth/login",
                json={"email": f"ratelimit{idx}@example.com", "password": "BadPassword@123"},
            )
            statuses.append(resp.status_code)

        assert 429 in statuses
    finally:
        limiter.reset()
        limiter.init_app(app)
