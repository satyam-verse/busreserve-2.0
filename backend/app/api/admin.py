"""Protected Admin Control Centre REST API."""

from datetime import date

from flask import Blueprint, g, jsonify, request

from app.ai import (
    clear_ai_history,
    get_ai_history,
    get_ai_manager,
    run_admin_ai_assistant,
)
from app.extensions import limiter
from app.models import AIConversationMessage
from app.services.admin_service import (
    admin_cancel_booking,
    admin_cancel_trip,
    admin_create_bus,
    admin_create_city,
    admin_create_route,
    admin_create_schedule,
    admin_delete_bus,
    admin_delete_city,
    admin_delete_route,
    admin_delete_schedule,
    admin_process_refund,
    admin_toggle_schedule,
    admin_update_bus,
    admin_update_city,
    admin_update_route,
    admin_update_schedule,
    get_admin_booking_detail,
    get_protected_admin_overview,
    list_admin_bookings,
    list_admin_buses,
    list_admin_cities,
    list_admin_routes,
    list_admin_schedules,
    list_admin_users,
    update_admin_user,
)
from app.utils.auth import ai_rate_limit_key, require_admin
from app.utils.errors import ValidationAPIError
from app.utils.schemas import (
    AdminAIChatSchema,
    AdminBookingCancelSchema,
    AdminBookingRefundSchema,
    AdminBusCreateSchema,
    AdminBusUpdateSchema,
    AdminCityCreateSchema,
    AdminCityUpdateSchema,
    AdminRouteCreateSchema,
    AdminRouteUpdateSchema,
    AdminScheduleCreateSchema,
    AdminScheduleUpdateSchema,
    AdminUserUpdateSchema,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

_user_update_schema = AdminUserUpdateSchema()
_city_create_schema = AdminCityCreateSchema()
_city_update_schema = AdminCityUpdateSchema()
_route_create_schema = AdminRouteCreateSchema()
_route_update_schema = AdminRouteUpdateSchema()
_bus_create_schema = AdminBusCreateSchema()
_bus_update_schema = AdminBusUpdateSchema()
_schedule_create_schema = AdminScheduleCreateSchema()
_schedule_update_schema = AdminScheduleUpdateSchema()
_booking_cancel_schema = AdminBookingCancelSchema()
_booking_refund_schema = AdminBookingRefundSchema()
_admin_ai_chat_schema = AdminAIChatSchema()


def _json_body(allow_empty: bool = False) -> dict:
    raw = request.get_json(silent=True)
    if raw is None and allow_empty:
        return {}
    if not isinstance(raw, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")
    return raw


def _parse_bool_arg(name: str) -> bool | None:
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return None
    val = raw.strip().lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    raise ValidationAPIError(f"Invalid boolean query parameter '{name}'.")


def _parse_pagination() -> tuple[int, int]:
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", default=20, type=int)))
    return page, per_page


# ---------------------------------------------------------------------------
# Analytics & Overview
# ---------------------------------------------------------------------------


@admin_bp.get("/overview")
@admin_bp.get("/analytics")
@require_admin
def admin_overview():
    """Return full database-driven overview, demo revenue, trends, and occupancy."""
    return jsonify(get_protected_admin_overview()), 200


# ---------------------------------------------------------------------------
# Users Management
# ---------------------------------------------------------------------------


@admin_bp.get("/users")
@require_admin
def get_users():
    page, per_page = _parse_pagination()
    payload = list_admin_users(
        query=request.args.get("q"),
        role=request.args.get("role"),
        is_active=_parse_bool_arg("is_active"),
        email_verified=_parse_bool_arg("email_verified"),
        page=page,
        per_page=per_page,
    )
    return jsonify(payload), 200


@admin_bp.patch("/users/<int:user_id>")
@require_admin
def patch_user(user_id: int):
    data = _user_update_schema.load(_json_body())
    updated = update_admin_user(g.current_user, user_id, data)
    return jsonify({"message": "User updated.", "user": updated.to_dict()}), 200


# ---------------------------------------------------------------------------
# Bookings & Demo Refund Management
# ---------------------------------------------------------------------------


@admin_bp.get("/bookings")
@require_admin
def get_bookings():
    page, per_page = _parse_pagination()
    if "limit" in request.args and "per_page" not in request.args:
        per_page = min(100, max(1, request.args.get("limit", default=20, type=int)))

    raw_date = request.args.get("travel_date")
    parsed_date = None
    if raw_date and raw_date.strip():
        try:
            parsed_date = date.fromisoformat(raw_date.strip())
        except ValueError as exc:
            raise ValidationAPIError(
                "Invalid travel_date format; use YYYY-MM-DD.",
                details={"travel_date": ["Expected ISO date YYYY-MM-DD."]},
            ) from exc

    payload = list_admin_bookings(
        status=request.args.get("status"),
        refund_status=request.args.get("refund_status"),
        travel_date=parsed_date,
        query=request.args.get("q"),
        page=page,
        per_page=per_page,
    )
    return jsonify(payload), 200


@admin_bp.get("/bookings/<string:pnr>")
@require_admin
def get_booking_detail_endpoint(pnr: str):
    detail = get_admin_booking_detail(pnr)
    return jsonify({"booking": detail}), 200


@admin_bp.post("/bookings/<string:pnr>/cancel")
@require_admin
def cancel_any_booking(pnr: str):
    data = _booking_cancel_schema.load(_json_body(allow_empty=True))
    booking = admin_cancel_booking(
        pnr,
        reason=data.get("reason"),
        process_refund=bool(data.get("process_refund", True)),
    )
    return jsonify(
        {
            "message": f"Booking {booking.pnr} cancelled by administrator.",
            "booking": booking.to_dict(),
        }
    ), 200


@admin_bp.post("/bookings/<string:pnr>/refund")
@require_admin
def refund_booking_endpoint(pnr: str):
    data = _booking_refund_schema.load(_json_body(allow_empty=True))
    booking = admin_process_refund(
        pnr,
        amount=data.get("amount"),
        note=data.get("note"),
    )
    return jsonify(
        {
            "message": f"Demo refund processed for {booking.pnr}.",
            "booking": booking.to_dict(),
        }
    ), 200


# ---------------------------------------------------------------------------
# City Management
# ---------------------------------------------------------------------------


@admin_bp.get("/cities")
@require_admin
def get_cities():
    page, per_page = _parse_pagination()
    payload = list_admin_cities(
        query=request.args.get("q"),
        state=request.args.get("state"),
        is_active=_parse_bool_arg("is_active"),
        page=page,
        per_page=per_page,
    )
    return jsonify(payload), 200


@admin_bp.post("/cities")
@require_admin
def create_city_endpoint():
    data = _city_create_schema.load(_json_body())
    city = admin_create_city(data)
    return jsonify({"city": city.to_dict()}), 201


@admin_bp.patch("/cities/<int:city_id>")
@require_admin
def update_city_endpoint(city_id: int):
    data = _city_update_schema.load(_json_body())
    city = admin_update_city(city_id, data)
    return jsonify({"city": city.to_dict()}), 200


@admin_bp.delete("/cities/<int:city_id>")
@require_admin
def delete_city_endpoint(city_id: int):
    admin_delete_city(city_id)
    return jsonify({"message": "City deleted."}), 200


# ---------------------------------------------------------------------------
# Route Management
# ---------------------------------------------------------------------------


@admin_bp.get("/routes")
@require_admin
def get_routes():
    page, per_page = _parse_pagination()
    payload = list_admin_routes(
        query=request.args.get("q"),
        source=request.args.get("source"),
        destination=request.args.get("destination"),
        page=page,
        per_page=per_page,
    )
    return jsonify(payload), 200


@admin_bp.post("/routes")
@require_admin
def create_route_endpoint():
    data = _route_create_schema.load(_json_body())
    route = admin_create_route(data)
    return jsonify({"route": route.to_dict(include_stops=True)}), 201


@admin_bp.patch("/routes/<int:route_id>")
@require_admin
def update_route_endpoint(route_id: int):
    data = _route_update_schema.load(_json_body())
    route = admin_update_route(route_id, data)
    return jsonify({"route": route.to_dict(include_stops=True)}), 200


@admin_bp.delete("/routes/<int:route_id>")
@require_admin
def delete_route_endpoint(route_id: int):
    admin_delete_route(route_id)
    return jsonify({"message": "Route deleted."}), 200


# ---------------------------------------------------------------------------
# Bus Fleet Management
# ---------------------------------------------------------------------------


@admin_bp.get("/buses")
@require_admin
def get_buses():
    page, per_page = _parse_pagination()
    payload = list_admin_buses(
        query=request.args.get("q"),
        bus_type=request.args.get("bus_type"),
        seat_layout=request.args.get("seat_layout"),
        is_active=_parse_bool_arg("is_active"),
        page=page,
        per_page=per_page,
    )
    return jsonify(payload), 200


@admin_bp.post("/buses")
@require_admin
def create_bus_endpoint():
    data = _bus_create_schema.load(_json_body())
    bus = admin_create_bus(data)
    return jsonify({"bus": bus.to_dict()}), 201


@admin_bp.patch("/buses/<int:bus_id>")
@require_admin
def update_bus_endpoint(bus_id: int):
    data = _bus_update_schema.load(_json_body())
    bus = admin_update_bus(bus_id, data)
    return jsonify({"bus": bus.to_dict()}), 200


@admin_bp.delete("/buses/<int:bus_id>")
@require_admin
def delete_bus_endpoint(bus_id: int):
    admin_delete_bus(bus_id)
    return jsonify({"message": "Bus deleted."}), 200


# ---------------------------------------------------------------------------
# Schedule & Trip Management
# ---------------------------------------------------------------------------


@admin_bp.get("/schedules")
@require_admin
def get_schedules():
    page, per_page = _parse_pagination()
    payload = list_admin_schedules(
        query=request.args.get("q"),
        route_id=request.args.get("route_id", type=int),
        bus_id=request.args.get("bus_id", type=int),
        is_active=_parse_bool_arg("is_active"),
        page=page,
        per_page=per_page,
    )
    return jsonify(payload), 200


@admin_bp.post("/schedules")
@require_admin
def create_schedule_endpoint():
    data = _schedule_create_schema.load(_json_body())
    schedule, gen_counts = admin_create_schedule(data)
    return jsonify({"schedule": schedule.to_dict(), "generated": gen_counts}), 201


@admin_bp.patch("/schedules/<int:schedule_id>")
@require_admin
def update_schedule_endpoint(schedule_id: int):
    raw = _json_body()
    # Preserve backwards compatibility for simple {is_active: bool} toggle calls
    if set(raw.keys()) == {"is_active"}:
        schedule = admin_toggle_schedule(schedule_id, bool(raw["is_active"]))
        return jsonify({"schedule": schedule.to_dict()}), 200
    data = _schedule_update_schema.load(raw)
    schedule = admin_update_schedule(schedule_id, data)
    return jsonify({"schedule": schedule.to_dict()}), 200


@admin_bp.delete("/schedules/<int:schedule_id>")
@require_admin
def delete_schedule_endpoint(schedule_id: int):
    admin_delete_schedule(schedule_id)
    return jsonify({"message": "Schedule deleted."}), 200


@admin_bp.post("/trips/<int:trip_id>/cancel")
@require_admin
def cancel_trip_endpoint(trip_id: int):
    trip = admin_cancel_trip(trip_id)
    return jsonify({"message": "Trip cancelled.", "trip": trip.to_dict()}), 200


# ---------------------------------------------------------------------------
# Phase 4: Read-Only Admin AI Operations Copilot & Provider Health
# ---------------------------------------------------------------------------


@admin_bp.post("/ai/chat")
@limiter.limit("30 per minute", key_func=ai_rate_limit_key)
@require_admin
def admin_ai_chat_endpoint():
    """Protected read-only AI Operations Copilot grounded in PostgreSQL overview metrics."""
    data = _admin_ai_chat_schema.load(_json_body())
    payload = run_admin_ai_assistant(g.current_user, data)
    return jsonify(payload), 200


@admin_bp.get("/ai/status")
@require_admin
def admin_ai_status_endpoint():
    """Return Gemini / Local Fallback provider status, health, and daily usage counters."""
    status = get_ai_manager().get_status(user_id=g.current_user.id)
    return jsonify(
        {
            "success": True,
            "provider": status["active_provider"],
            "mode": status["mode"],
            "model": status["model"],
            "fallback_used": status["active_provider"] != "gemini",
            "status": status,
        }
    ), 200


@admin_bp.get("/ai/history")
@require_admin
def admin_ai_history_endpoint():
    """Return isolated Admin Copilot conversation turns for the signed-in admin."""
    limit = request.args.get("limit", type=int)
    messages = get_ai_history(
        g.current_user.id,
        portal=AIConversationMessage.PORTAL_ADMIN,
        limit=limit,
    )
    return jsonify({"success": True, "messages": messages, "count": len(messages)}), 200


@admin_bp.delete("/ai/history")
@require_admin
def delete_admin_ai_history_endpoint():
    """Delete isolated Admin Copilot conversation turns for the signed-in admin."""
    deleted = clear_ai_history(
        g.current_user.id,
        portal=AIConversationMessage.PORTAL_ADMIN,
    )
    return jsonify(
        {
            "success": True,
            "message": "Admin AI copilot history cleared.",
            "deleted_count": deleted,
        }
    ), 200
