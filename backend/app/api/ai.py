"""Protected Passenger AI assistant, recommendation, and history API endpoints."""

from flask import Blueprint, g, jsonify, request

from app.ai import (
    clear_ai_history,
    get_ai_history,
    get_ai_manager,
    run_passenger_assistant,
    run_recommendations_engine,
)
from app.extensions import limiter
from app.models import AIConversationMessage
from app.utils.auth import ai_rate_limit_key, require_auth
from app.utils.errors import ValidationAPIError
from app.utils.schemas import AIChatSchema, AIRecommendationSchema

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

_chat_schema = AIChatSchema()
_rec_schema = AIRecommendationSchema()


def _json_body(allow_empty: bool = False) -> dict:
    raw = request.get_json(silent=True)
    if raw is None and allow_empty:
        return {}
    if not isinstance(raw, dict):
        raise ValidationAPIError("Request body must be a valid JSON object.")
    return raw


@ai_bp.post("/chat")
@limiter.limit("30 per minute", key_func=ai_rate_limit_key)
@require_auth
def passenger_ai_chat():
    """Conversational AI Passenger Assistant backed by Gemini + Local Fallback."""
    data = _chat_schema.load(_json_body())
    payload = run_passenger_assistant(g.current_user, data, endpoint_mode="chat")
    return jsonify(payload), 200


@ai_bp.post("/travel-assistant")
@limiter.limit("30 per minute", key_func=ai_rate_limit_key)
@require_auth
def passenger_travel_assistant():
    """Structured travel-assistant endpoint combining NLP parsing + live recommendations."""
    data = _chat_schema.load(_json_body())
    payload = run_passenger_assistant(g.current_user, data, endpoint_mode="travel_assistant")
    return jsonify(payload), 200


@ai_bp.post("/recommendations")
@limiter.limit("30 per minute", key_func=ai_rate_limit_key)
@require_auth
def passenger_recommendations():
    """Smart route & schedule recommendations grounded strictly in PostgreSQL."""
    data = _rec_schema.load(_json_body(allow_empty=True))
    payload = run_recommendations_engine(data, user=g.current_user)
    return jsonify(payload), 200


@ai_bp.get("/status")
@require_auth
def ai_status():
    """Return safe AI provider health, mode, and non-secret daily quota telemetry."""
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


@ai_bp.get("/history")
@require_auth
def passenger_ai_history():
    """Retrieve isolated conversation history belonging solely to the current user."""
    limit = request.args.get("limit", type=int)
    messages = get_ai_history(
        g.current_user.id,
        portal=AIConversationMessage.PORTAL_PASSENGER,
        limit=limit,
    )
    return jsonify(
        {
            "success": True,
            "messages": messages,
            "count": len(messages),
        }
    ), 200


@ai_bp.delete("/history")
@require_auth
def delete_passenger_ai_history():
    """Delete only the caller's own passenger AI conversation history."""
    deleted = clear_ai_history(
        g.current_user.id,
        portal=AIConversationMessage.PORTAL_PASSENGER,
    )
    return jsonify(
        {
            "success": True,
            "message": "Your AI conversation history has been cleared.",
            "deleted_count": deleted,
        }
    ), 200
