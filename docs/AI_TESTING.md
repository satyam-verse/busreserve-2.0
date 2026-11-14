# BusReserve 2.0 — AI Testing Guide

## Automated Verification Scope (`backend/tests/test_ai_phase4.py`)
Automated tests execute against a real PostgreSQL 16 database while mocking `google-genai` SDK client responses cleanly so tests stay fast, deterministic, and never consume live Gemini free-tier quota:
- Gemini happy path (`provider=gemini`, `mode=gemini`, `fallback_used=false`).
- Missing API key, `GEMINI_ENABLED=false`, and `AI_PROVIDER=local_fallback` fallback paths.
- HTTP `429` rate-limit retries and fallback, timeout retries and fallback, non-retry `401`/`403` auth failure immediate fallback, and malformed/empty output safety.
- Cooldown expiration and automatic recovery back to Gemini.
- Atomic PostgreSQL daily global (`AI_DAILY_REQUEST_LIMIT`) and per-user (`AI_USER_DAILY_LIMIT`) quota enforcement.
- Dynamic PostgreSQL city/alias extraction, IST (`Asia/Kolkata`) relative/ISO date parsing, out-of-horizon rejection, recommendation scoring (`cheapest`, `earliest`, `overnight`, `shortest`, `most_seats`, `max_budget`, `WINDOW` seats), sold-out exclusion, and admin-created city/route/schedule discovery.
- Unauthenticated `401` checks and Passenger vs Admin `403` RBAC isolation.
- Cross-user conversation history isolation, own-PNR boundary enforcement, and `DELETE /api/ai/history`.
- Admin Copilot analytics grounding (no write side effects).
- Prompt-injection / secret-exfiltration refusal and Flask-Limiter rate-limit enforcement.
- Startup configuration validation (`validate_ai_config`) and deprecated model override (`gemini-2.0-*` -> `gemini-3.8-flash`).

## Running Backend Tests
```powershell
cd backend
.\.venv\Scripts\pytest.exe -vv tests/test_ai_phase4.py
.\.venv\Scripts\pytest.exe -vv
.\.venv\Scripts\ruff.exe check app tests migrations wsgi.py scripts
```
