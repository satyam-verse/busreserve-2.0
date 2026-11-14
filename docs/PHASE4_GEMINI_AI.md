# BusReserve 2.0 — Phase 4: Gemini AI Intelligence Integration

## Overview
Phase 4 introduces a modular, backend-only AI intelligence layer for BusReserve 2.0 powered by the official Google GenAI SDK (`google-genai >= 2.25.0`) with an automatic deterministic `LocalFallbackProvider`. Every response is strictly grounded in real PostgreSQL data returned by existing domain services (`booking_service`, `schedule_service`, `admin_service`) without altering transactional seat locking, PNR booking, or RBAC guarantees.

## Key Capabilities
1. **Free-Tier-First Gemini Provider (`gemini-3.8-flash`)**:
   - Invokes `google.genai.Client` (`client.interactions.create(..., store=False)`) strictly from the Flask backend.
   - Controlled exponential-backoff retries on transient `429` / `5xx` / timeout errors; immediate non-retry fallback on `401` / `403` authentication failures.
2. **Automatic Deterministic Local Fallback**:
   - Seamlessly handles passenger travel queries, recommendations, booking/cancellation guidance, PNR lookups, and admin analytics even when `GEMINI_API_KEY` is unset, `GEMINI_ENABLED=false`, daily quota is exhausted, or Gemini API calls time out/fail.
   - Tracks provider health cooldown (`AI_RECOVERY_COOLDOWN_SECONDS`) and automatically probes recovery once cooldown elapses.
3. **Smart Route & Trip Recommendation Engine**:
   - Extracts origin/destination cities dynamically from PostgreSQL (`cities` + aliases + route stops), IST dates (`Asia/Kolkata` within `BOOKING_HORIZON_DAYS`), time-of-day windows, budget caps, seat count, bus type, and preference (`cheapest`, `earliest`, `overnight`, `shortest`, `most_seats`, `balanced`).
   - Returns clickable trip cards backed directly by live `Trip` and `TripSeat` rows.
4. **Isolated Conversation Retention**:
   - Stores turns in `ai_conversation_messages` scoped by `(user_id, portal)`.
   - Supports retrieval (`GET /api/ai/history`) and deletion (`DELETE /api/ai/history`).
5. **Read-Only Admin AI Operations Copilot**:
   - Protected by `@require_admin` under `/api/admin/ai/*`, grounded in `get_protected_admin_overview()` and safe provider telemetry.

## Environment Variables
| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | empty | Backend-only Google Gemini API key (placeholder only in `.env.example`) |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Target Gemini model |
| `GEMINI_ENABLED` | `true` | Enable/disable Gemini calls globally |
| `AI_PROVIDER` | `auto` | `auto`, `gemini`, or `local_fallback` |
| `AI_TIMEOUT_SECONDS` | `15` | Per-request Gemini HTTP timeout (`1`–`60` seconds) |
| `AI_MAX_RETRIES` | `2` | Controlled retry attempts on transient errors (`0`–`5`) |
| `AI_DAILY_REQUEST_LIMIT` | `200` | Global daily Gemini call budget (IST date) |
| `AI_USER_DAILY_LIMIT` | `50` | Per-user daily Gemini call budget (IST date) |
| `AI_MAX_INPUT_LENGTH` | `1000` | Maximum passenger/admin prompt character length |
| `AI_MAX_OUTPUT_TOKENS` | `600` | Maximum output tokens per Gemini response |
| `AI_HISTORY_LIMIT` | `20` | Default retained conversation history window per retrieval |
| `AI_RECOVERY_COOLDOWN_SECONDS` | `60` | Cooldown window before automatic Gemini recovery probe |
