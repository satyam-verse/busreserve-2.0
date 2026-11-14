# BusReserve 2.0 — AI Architecture

## Module Layout (`backend/app/ai/`)
- `providers.py`:
  - `BaseAIProvider`: Abstract provider contract (`generate(...) -> ProviderResult`).
  - `GeminiProvider`: Official `google-genai` SDK integration (`interactions.create` with `store=False`, `HttpOptions(timeout=int(timeout*1000))`, key redaction, error classification, controlled retries).
  - `LocalFallbackProvider`: Zero-external-dependency PostgreSQL-grounded deterministic responder for both Passenger and Admin portals.
  - `AIProviderManager`: Coordinates provider eligibility (`AI_PROVIDER`, `GEMINI_ENABLED`, key presence, daily global/per-user PostgreSQL quota counters in `ai_usage_daily`), failure cooldowns, automatic fallback, and automatic recovery probes.
- `nlp.py`:
  - `sanitize_user_input`: Control-character stripping, max-length clamping, and prompt-injection/exfiltration detection.
  - `extract_travel_preferences`: Resolves dynamic cities/aliases from PostgreSQL, `Asia/Kolkata` relative/explicit dates within the 90-day horizon, budgets, seat counts, time windows, bus types, PNRs, and intents.
- `recommendations.py`:
  - `RecommendationEngine`: Calls `app.services.booking_service.search_trips`, excludes sold-out trips and out-of-horizon dates, filters by budget/time window/bus type, inspects seat-type counts (`WINDOW` / `AISLE`), and ranks real trips with transparent reason badges.
- `assistant_service.py`:
  - Orchestrates `run_passenger_assistant`, `run_recommendations_engine`, `run_admin_ai_assistant`, `get_ai_history`, and `clear_ai_history`.
  - Strips PII (passenger email/phone) before preparing external LLM context and verifies strict booking PNR ownership (`booking.user_id == user.id`).

## Database Tables (Migration `9b2e7c14f8a1`)
1. `ai_conversation_messages`:
   - `id`, `user_id` (`FK users.id ON DELETE CASCADE`), `portal` (`PASSENGER` | `ADMIN`), `role` (`user` | `assistant`), `content`, `provider`, `mode`, `intent`, `fallback_used`, `metadata_json`, `created_at`.
2. `ai_usage_daily`:
   - `id`, `usage_date`, `scope_key` (`global` or `user:<id>`), `gemini_requests`, `fallback_requests`, `failed_requests`, `updated_at` with unique constraint `uq_ai_usage_daily_scope`.
   - Updated atomically via PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` so Gunicorn worker processes share accurate daily quota limits.

## Request Flow
```text
Client Request (/api/ai/* or /api/admin/ai/*)
  -> Flask-Limiter + Auth/RBAC (@require_auth / @require_admin)
  -> Marshmallow Schema Validation + Input Sanitization & Injection Guardrail
  -> Live PostgreSQL Grounding (cities, routes, trips, seats, caller bookings / admin overview)
  -> AIProviderManager
       ├─ Eligible & healthy & within IST daily quota -> GeminiProvider (official google-genai SDK)
       └─ Disabled / unconfigured / quota reached / timeout / 429 / 401 -> LocalFallbackProvider
  -> Persist Turn (scoped strictly by user_id + portal) -> JSON Response
```
