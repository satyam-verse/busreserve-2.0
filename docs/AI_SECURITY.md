# BusReserve 2.0 — AI Security & Privacy Controls

1. **Backend-Only Key Management**:
   - `GEMINI_API_KEY` is read exclusively by the Flask backend (`BaseConfig` / `GeminiProvider`) and never serialized in API payloads, frontend bundles, `.env.example`, or structured JSON logs.
   - Placeholder strings (`your-gemini-api-key-here`, `REPLACE_ME`, `changeme`) are normalized to empty string during startup validation so the server starts safely in fallback mode.
   - Exception strings caught from SDK calls pass through `_redact_secret` before logging.
   - `client.interactions.create(..., store=False)` opts out of server-side Gemini interaction retention.

2. **Authentication, RBAC & Isolation**:
   - All `/api/ai/*` endpoints enforce `@require_auth` (`401` when unauthenticated).
   - All `/api/admin/ai/*` endpoints enforce `@require_admin` (`403` for passenger accounts).
   - Conversation history queries filter strictly by `(user_id, portal)`.
   - PNR lookups inside passenger chat verify `booking.user_id == g.current_user.id`, preventing enumeration or access to guest/other-user bookings.

3. **Prompt-Injection & Data-Leak Guardrails**:
   - `sanitize_user_input` strips unsafe control characters, enforces `AI_MAX_INPUT_LENGTH`, and intercepts instruction-override, SQL-dumping, credential-exfiltration, and cross-user probing patterns before Gemini is invoked.
   - Passenger PII (`passenger_email`, `passenger_phone`, `password_hash`, `AuthSession` tokens) is stripped from prompt contexts.

4. **Strict Anti-Hallucination & Read-Only Boundaries**:
   - AI assistants never execute direct SQL mutations, seat reservations, cancellations, refunds, or admin changes.
   - Booking links and trip cards come exclusively from validated PostgreSQL records.

5. **Quota & Rate-Limiting Protection**:
   - Per-user/IP endpoint throttling via Flask-Limiter (`30 per minute`).
   - Atomic daily Gemini call limits in PostgreSQL (`AI_DAILY_REQUEST_LIMIT` global and `AI_USER_DAILY_LIMIT` per user) with automatic fallback to deterministic local responses.
