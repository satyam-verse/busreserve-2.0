# BusReserve 2.0 — AI REST API Reference

All AI endpoints return a consistent top-level envelope:
```json
{
  "success": true,
  "provider": "gemini | local_fallback",
  "mode": "gemini | local_fallback",
  "model": "gemini-3.8-flash | deterministic-local-v1",
  "message": "Grounded assistant response text",
  "intent": "trip_recommendation | pnr_lookup | my_bookings | cancellation_refund_guidance | booking_guidance | horizon_info | route_info | admin_analytics | security_refusal | general_help",
  "fallback_used": false,
  "fallback_reason": null,
  "data": {}
}
```

## Passenger Endpoints (`@require_auth`)

### 1. `POST /api/ai/chat`
Rate limit: `30 per minute` per user/IP.
- Request JSON: `{"message": "Cheapest AC bus from Patna to Ranchi tomorrow under ₹800"}` (optional structured hints: `source`, `destination`, `travel_date`, `max_budget`, `min_seats`, `preference`, `time_window`, `bus_type`, `seat_preference`).
- `data` includes `parsed_query`, `recommendations`, `filters_relaxed`, `routes`, `booking_horizon`, `user_bookings_count`.

### 2. `POST /api/ai/travel-assistant`
Rate limit: `30 per minute` per user/IP.
- Same validated schema as `/api/ai/chat`; always runs `RecommendationEngine` alongside conversational guidance.

### 3. `POST /api/ai/recommendations`
Rate limit: `30 per minute` per user/IP.
- Request JSON: `{"query": "...", "source": "...", "destination": "...", "travel_date": "YYYY-MM-DD", "max_budget": 900, "min_seats": 1, "preference": "cheapest|earliest|overnight|shortest|most_seats|balanced", "time_window": "early_morning|morning|afternoon|evening|overnight", "bus_type": "...", "seat_preference": "WINDOW|AISLE", "limit": 5}`.

### 4. `GET /api/ai/status`
- Returns current provider (`gemini` vs `local_fallback`), `model`, health flags, cooldown seconds remaining, and caller's safe daily quota usage without exposing API keys.

### 5. `GET /api/ai/history`
- Query param: `limit` (optional integer, capped at `100`; defaults to `AI_HISTORY_LIMIT`).
- Returns only messages belonging strictly to `g.current_user.id` in the `PASSENGER` portal.

### 6. `DELETE /api/ai/history`
- Deletes only messages belonging strictly to `g.current_user.id` in the `PASSENGER` portal.

## Admin Endpoints (`@require_admin`)
Passenger tokens (`USER` role) receive HTTP `403 Forbidden`; anonymous callers receive HTTP `401 Unauthorized`.

### 7. `POST /api/admin/ai/chat`
Rate limit: `30 per minute` per admin user/IP.
- Request JSON: `{"message": "Summarize confirmed bookings and pending refunds"}`.
- Grounded in `get_protected_admin_overview()` and `AIProviderManager.get_status()`. Strictly read-only.

### 8. `GET /api/admin/ai/status`
- Returns full global/admin provider health, error reason, cooldown state, and daily usage telemetry.

### 9. `GET /api/admin/ai/history` & `DELETE /api/admin/ai/history`
- Reads or clears isolated `ADMIN` portal conversation history for the authenticated administrator.
