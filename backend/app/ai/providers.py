"""Modular AI provider abstraction: Google Gemini API (official SDK) + Local Fallback."""

from __future__ import annotations

import logging
import math
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from flask import current_app
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models.ai import AIUsageDaily
from app.utils.timezone import get_app_today

logger = logging.getLogger("busreserve.ai.providers")


class AIProviderError(Exception):
    """Classified failure raised by an external AI provider before fallback."""

    def __init__(
        self,
        reason: str,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.retryable = retryable
        self.status_code = status_code


@dataclass
class ProviderResult:
    """Normalized response returned by any AI provider."""

    text: str
    provider: str
    mode: str
    model: str | None = None
    fallback_used: bool = False
    reason: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0

    def to_metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "mode": self.mode,
            "model": self.model,
            "fallback_used": self.fallback_used,
            "reason": self.reason,
            "latency_ms": self.latency_ms,
        }


def _redact_secret(text: str, secret: str) -> str:
    if not secret or len(secret) < 6:
        return text
    return text.replace(secret, "[REDACTED]")


class BaseAIProvider(ABC):
    """Abstract provider interface implemented by Gemini and Local Fallback providers."""

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        *,
        system_instruction: str,
        prompt: str,
        fallback_context: dict[str, Any],
        temperature: float = 0.3,
    ) -> ProviderResult:
        """Generate a textual response for the prepared grounded prompt/context."""


class GeminiProvider(BaseAIProvider):
    """Google Gemini API provider powered by the official `google-genai` SDK."""

    name = "gemini"

    def __init__(self, sleep_fn: Callable[[float], None] | None = None) -> None:
        self._sleep = sleep_fn or time.sleep

    def _build_client(self, api_key: str, timeout_seconds: float):
        from google import genai
        from google.genai import types as genai_types

        return genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                # Disable SDK-level retries so GeminiProvider's bounded retry/backoff
                # and LocalFallbackProvider failover stay well inside Gunicorn's timeout.
                retry_options=genai_types.HttpRetryOptions(attempts=1),
            ),
        )

    def _classify_exception(self, exc: Exception, api_key: str) -> AIProviderError:
        from google.genai import errors as genai_errors

        safe_msg = _redact_secret(str(exc), api_key)
        lowered = safe_msg.lower()

        if isinstance(exc, TimeoutError) or "timed out" in lowered or "timeout" in lowered:
            return AIProviderError("timeout", "Gemini request timed out.", retryable=True)

        if exc.__class__.__name__ in {"TimeoutException", "ReadTimeout", "ConnectTimeout"}:
            return AIProviderError("timeout", "Gemini HTTP request timed out.", retryable=True)

        if isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None)
            status_text = str(getattr(exc, "status", "") or "").upper()
            if code == 429 or "RESOURCE_EXHAUSTED" in status_text or "QUOTA" in lowered:
                return AIProviderError(
                    "rate_limited",
                    "Gemini rate limit or free-tier quota exceeded.",
                    retryable=True,
                    status_code=code or 429,
                )
            if code in (401, 403) or status_text in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
                return AIProviderError(
                    "auth_error",
                    "Gemini authentication failed.",
                    retryable=False,
                    status_code=code,
                )
            if code is not None and 500 <= int(code) < 600:
                return AIProviderError(
                    "provider_error",
                    f"Gemini service error ({code}).",
                    retryable=True,
                    status_code=code,
                )
            return AIProviderError(
                "provider_error",
                f"Gemini API error ({code or 'unknown'}). ",
                retryable=False,
                status_code=code,
            )

        if "429" in lowered or "quota" in lowered or "resource_exhausted" in lowered:
            return AIProviderError("rate_limited", "Gemini quota exceeded.", retryable=True)
        if "401" in lowered or "403" in lowered or "api key" in lowered:
            return AIProviderError("auth_error", "Gemini credential error.", retryable=False)

        return AIProviderError(
            "provider_error", f"Gemini request failed: {type(exc).__name__}", retryable=True
        )

    @staticmethod
    def _extract_usage(interaction: Any) -> dict[str, Any]:
        usage = getattr(interaction, "usage", None)
        if usage is None:
            return {}
        return {
            "total_input_tokens": getattr(usage, "total_input_tokens", None),
            "total_output_tokens": getattr(usage, "total_output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    def generate(
        self,
        *,
        system_instruction: str,
        prompt: str,
        fallback_context: dict[str, Any],
        temperature: float = 0.3,
        model_override: str | None = None,
    ) -> ProviderResult:
        api_key = str(current_app.config.get("GEMINI_API_KEY") or "").strip()
        if not api_key:
            raise AIProviderError(
                "missing_api_key", "GEMINI_API_KEY is not configured.", retryable=False
            )

        model_name = (
            model_override or str(current_app.config.get("GEMINI_MODEL") or "gemini-3.8-flash")
        ).strip()
        timeout_seconds = float(current_app.config.get("AI_TIMEOUT_SECONDS", 15.0))
        max_retries = int(current_app.config.get("AI_MAX_RETRIES", 2))
        max_output_tokens = int(current_app.config.get("AI_MAX_OUTPUT_TOKENS", 600))

        client = self._build_client(api_key, timeout_seconds)
        last_error: AIProviderError | None = None

        for attempt in range(max_retries + 1):
            started = time.monotonic()
            try:
                interaction = client.interactions.create(
                    model=model_name,
                    input=prompt,
                    system_instruction=system_instruction,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    },
                    store=False,
                    timeout=timeout_seconds,
                )
                latency_ms = int((time.monotonic() - started) * 1000)
                status = str(getattr(interaction, "status", "completed") or "completed").lower()
                text = str(getattr(interaction, "output_text", "") or "").strip()

                if status in {"failed", "cancelled"} or not text:
                    raise AIProviderError(
                        "provider_error",
                        f"Gemini returned status '{status}' with empty output.",
                        retryable=(status == "failed"),
                    )

                return ProviderResult(
                    text=text,
                    provider=self.name,
                    mode="gemini",
                    model=model_name,
                    fallback_used=False,
                    usage=self._extract_usage(interaction),
                    latency_ms=latency_ms,
                )
            except AIProviderError as classified:
                last_error = classified
            except Exception as exc:  # noqa: BLE001 - map SDK/network/timeout cleanly
                last_error = self._classify_exception(exc, api_key)

            if not last_error.retryable or attempt >= max_retries:
                raise last_error

            backoff_seconds = min(2.0, 0.35 * (2**attempt))
            logger.warning(
                "gemini_retry_scheduled",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "reason": last_error.reason,
                    "backoff_seconds": backoff_seconds,
                },
            )
            self._sleep(backoff_seconds)

        assert last_error is not None  # pragma: no cover
        raise last_error


class LocalFallbackProvider(BaseAIProvider):
    """Deterministic PostgreSQL-grounded local assistant with zero external dependencies."""

    name = "local_fallback"

    def generate(
        self,
        *,
        system_instruction: str,
        prompt: str,
        fallback_context: dict[str, Any],
        temperature: float = 0.0,
    ) -> ProviderResult:
        started = time.monotonic()
        portal = fallback_context.get("portal", "PASSENGER")
        if portal == "ADMIN":
            text = self._render_admin_response(fallback_context)
        else:
            text = self._render_passenger_response(fallback_context)
        latency_ms = int((time.monotonic() - started) * 1000)
        return ProviderResult(
            text=text,
            provider=self.name,
            mode="local_fallback",
            model="deterministic-local-v1",
            fallback_used=bool(fallback_context.get("fallback_triggered", True)),
            reason=fallback_context.get("fallback_reason"),
            latency_ms=latency_ms,
        )

    @staticmethod
    def _format_trip_line(idx: int, trip: dict[str, Any]) -> str:
        highlights = ", ".join(trip.get("reasons", [])[:2])
        badge = f" ({highlights})" if highlights else ""
        bus_label = trip["bus_type"].replace("_", " ")
        return (
            f"{idx}. **{trip['route_name']}** on **{trip['travel_date']}** "
            f"({trip['departure_time']} → {trip['arrival_time']}, {trip['duration_display']}) — "
            f"{trip['operator_name']} [{bus_label}, {trip['seat_layout']}], "
            f"**₹{trip['base_fare']:.0f}**, **{trip['available_seats']} seats open**{badge}."
        )

    def _render_passenger_response(self, ctx: dict[str, Any]) -> str:
        intent = ctx.get("intent", "general_help")
        horizon_days = ctx.get("booking_horizon_days", 90)
        min_date = ctx.get("min_date")
        max_date = ctx.get("max_date")

        if ctx.get("security_blocked"):
            return (
                "I can only assist with BusReserve travel planning, live schedules, "
                "seat availability, bookings, PNR checks, and cancellations. "
                "I cannot disclose system internals, credentials, or private user records."
            )

        if intent == "pnr_lookup":
            booking = ctx.get("pnr_booking")
            if booking:
                return (
                    f"Booking **{booking['pnr']}** is **{booking['status']}** "
                    f"(Refund: **{booking['refund_status']}**).\n"
                    f"- Route: {booking['route_name']} on {booking['travel_date']} "
                    f"at {booking['departure_time']}\n"
                    f"- Seat: {booking['seat_number']} • Fare: ₹{booking['total_fare']:.2f}\n"
                    f"- Boarding: {booking['boarding_stop']} → Drop: {booking['drop_stop']}\n"
                    "You can view full ticket details or cancel from **My Dashboard** or "
                    f"`/bookings/{booking['pnr']}`."
                )
            pnr = ctx.get("requested_pnr")
            if pnr:
                return (
                    f"I could not find an accessible booking matching PNR **{pnr}** "
                    "under your account. Verify the PNR in **Check PNR** (`/pnr`) "
                    "or check **My Dashboard** (`/dashboard`)."
                )
            return (
                "To check a ticket, include your PNR (for example `BR...`) or visit "
                "**Check PNR** (`/pnr`) or **My Dashboard → My Bookings**."
            )

        if intent == "my_bookings":
            recent = ctx.get("user_bookings") or []
            if not recent:
                return (
                    "You do not have any bookings recorded yet on your account. "
                    "Ask me for a route (e.g. *Patna to Ranchi tomorrow*) to find trips!"
                )
            lines = [f"Here are your latest {min(len(recent), 5)} account bookings:"]
            for b in recent[:5]:
                lines.append(
                    f"- **{b['pnr']}**: {b['route_name']} on {b['travel_date']} "
                    f"({b['departure_time']}), Seat {b['seat_number']}, "
                    f"₹{b['total_fare']:.0f} — **{b['status']}** (Refund: {b['refund_status']})"
                )
            lines.append("Open **My Dashboard** (`/dashboard`) anytime to view or cancel bookings.")
            return "\n".join(lines)

        if intent == "cancellation_refund_guidance":
            return (
                "To cancel a reservation and check demo refund status safely:\n"
                "1. Open **My Dashboard → My Bookings** (`/dashboard`) or **Check PNR** (`/pnr`).\n"
                "2. Select the confirmed booking and click **Cancel Booking** — PostgreSQL "
                "releases the seat immediately.\n"
                "3. Demo refund workflows mark eligible cancelled bookings as `PENDING` until "
                "processed (`PROCESSED`) — BusReserve runs demo workflows without real payments."
            )

        if intent == "booking_guidance":
            return (
                "Booking a seat takes four quick steps:\n"
                "1. Search any origin city, destination city, and IST date within the "
                f"**{horizon_days}-day** booking window ({min_date} to {max_date}).\n"
                "2. Pick a recommended trip (compare fare, times, bus type, open seats).\n"
                "3. Choose your seat on the interactive coach map "
                "(PostgreSQL atomic locks prevent double-booking).\n"
                "4. Confirm passenger details to receive your instant **PNR**."
            )

        if intent == "horizon_info":
            return (
                "BusReserve schedules operate in **Asia/Kolkata (IST)** with a rolling "
                f"**{horizon_days}-day booking window** covering **{min_date} to {max_date}**. "
                "Past dates are automatically blocked."
            )

        if ctx.get("out_of_horizon"):
            return (
                f"The requested travel date is outside the **{horizon_days}-day IST window** "
                f"({min_date} to {max_date}). Try asking for a date within that range."
            )

        recs = ctx.get("recommendations") or []
        parsed = ctx.get("parsed_query") or {}
        if recs:
            header_parts = []
            if parsed.get("source") and parsed.get("destination"):
                header_parts.append(f"from **{parsed['source']}** to **{parsed['destination']}**")
            elif parsed.get("source"):
                header_parts.append(f"departing **{parsed['source']}**")
            elif parsed.get("destination"):
                header_parts.append(f"arriving **{parsed['destination']}**")
            if parsed.get("travel_date"):
                header_parts.append(f"on **{parsed['travel_date']} (IST)**")
            scope = " ".join(header_parts) if header_parts else "across upcoming scheduled trips"
            lines = [f"Found **{len(recs)}** real-time bus options {scope}:"]
            for idx, item in enumerate(recs[:5], start=1):
                lines.append(self._format_trip_line(idx, item))
            lines.append(
                "Click **Select Seats** on any recommendation card below to open the seat map."
            )
            return "\n".join(lines)

        routes = ctx.get("routes_summary") or []
        if intent in {"trip_recommendation", "route_info"}:
            route_hint = ", ".join(f"{r['source']} → {r['destination']}" for r in routes[:5])
            return (
                "No scheduled trips matched your exact filters in the current database. "
                + (f"Active routes include: {route_hint}. " if route_hint else "")
                + f"Trips are searchable across **{min_date} to {max_date} (IST)**. "
                "Try relaxing your budget, time-of-day, or seat requirement."
            )

        cities_sample = ", ".join(c["name"] for c in (ctx.get("cities_sample") or [])[:8])
        return (
            "Hello! I am your **BusReserve AI Travel Assistant**. Ask me to:\n"
            "- Find buses (e.g. *Cheapest AC bus Patna to Ranchi tomorrow* or "
            "*Overnight sleeper under ₹800*)\n"
            f"- Explore {len(routes)} active routes across cities like "
            f"{cities_sample or 'India'}\n"
            "- Check PNR status, booking steps, or cancellation & demo refund policies."
        )

    def _render_admin_response(self, ctx: dict[str, Any]) -> str:
        overview = ctx.get("admin_overview") or {}
        summary = overview.get("summary") or {}
        popular = overview.get("popular_routes") or []
        occupancy = overview.get("trip_occupancy") or []
        status = ctx.get("ai_status") or {}

        if ctx.get("security_blocked"):
            return (
                "Security policy blocked this request. The Admin AI Copilot can summarize "
                "operational analytics and AI provider telemetry from PostgreSQL, "
                "but cannot expose secrets, credentials, or execute mutations."
            )

        question = (ctx.get("question") or "").lower()
        if any(w in question for w in ("ai", "gemini", "fallback", "quota", "provider")):
            q_info = status.get("quota") or {}
            active = status.get("active_provider", "unknown")
            cfg_mode = status.get("configured_provider")
            return (
                "**AI Provider Health Summary**\n"
                f"- Active provider: **{active}** (configured mode: `{cfg_mode}`)\n"
                f"- Gemini enabled/configured: **{status.get('gemini_enabled')} / "
                f"{status.get('gemini_configured')}** (`{status.get('model')}`)\n"
                f"- Healthy: **{status.get('healthy')}** • "
                f"Last error: `{status.get('last_error_reason') or 'none'}`\n"
                f"- Today's Gemini requests: **{q_info.get('global_used_today', 0)} / "
                f"{q_info.get('daily_limit', 0)}** "
                f"(remaining: {q_info.get('global_remaining_today', 0)})."
            )

        if popular:
            top = popular[0]
            top_route = (
                f"{top['route_name']} ({top['confirmed_bookings']} confirmed, "
                f"₹{top['demo_revenue']:.0f} demo rev)"
            )
        else:
            top_route = "No confirmed route bookings yet"
        high_occ = sorted(occupancy, key=lambda t: t.get("occupancy_rate", 0), reverse=True)[:3]
        occ_lines = [
            f"  - {t['route_name']} ({t['travel_date']} {t['departure_time']}): "
            f"{t['occupied_seats']}/{t['total_seats']} seats ({t['occupancy_rate']}%)"
            for t in high_occ
        ]

        return (
            "**BusReserve Operations Analytics Snapshot (Live PostgreSQL)**\n"
            f"- **Bookings**: {summary.get('confirmed_bookings', 0)} confirmed, "
            f"{summary.get('cancelled_bookings', 0)} cancelled "
            f"(Total: {summary.get('total_bookings', 0)})\n"
            f"- **Demo Revenue**: ₹{summary.get('demo_net_revenue', 0):.2f} confirmed net • "
            f"Pending refunds: {summary.get('pending_refunds_count', 0)}, "
            f"Processed: {summary.get('processed_refunds_count', 0)} "
            "(Demo metrics only — no real payments)\n"
            f"- **Fleet & Network**: {summary.get('active_cities', 0)}/"
            f"{summary.get('total_cities', 0)} cities, "
            f"{summary.get('total_routes', 0)} routes, {summary.get('active_buses', 0)}/"
            f"{summary.get('total_buses', 0)} buses, "
            f"{summary.get('active_schedules', 0)} schedules ({summary.get('total_trips', 0)} "
            f"trips over {summary.get('booking_horizon_days', 90)}d)\n"
            f"- **Seat Occupancy**: {summary.get('occupancy_rate', 0)}% "
            f"({summary.get('occupied_seats', 0)}/{summary.get('total_seats', 0)} seats)\n"
            f"- **Passengers**: {summary.get('active_users', 0)} active / "
            f"{summary.get('suspended_users', 0)} suspended "
            f"(Verified: {summary.get('verified_users', 0)}, "
            f"New 7d: {summary.get('new_users_7d', 0)})\n"
            f"- **Top Route**: {top_route}"
            + (
                "\n- **Highest Occupancy Upcoming Trips**:\n" + "\n".join(occ_lines)
                if occ_lines
                else ""
            )
        )


class AIProviderManager:
    """Coordinates Gemini API calls, quota guards, circuit recovery, and automatic fallback."""

    def __init__(
        self,
        gemini_provider: BaseAIProvider | None = None,
        fallback_provider: BaseAIProvider | None = None,
    ) -> None:
        self._gemini = gemini_provider or GeminiProvider()
        self._fallback = fallback_provider or LocalFallbackProvider()
        self._consecutive_failures: int = 0
        self._degraded_until_monotonic: float | None = None
        self._last_error_reason: str | None = None
        self._last_error_at: str | None = None
        self._last_success_at: str | None = None
        self._last_active_model: str | None = None
        self._last_model_failover: str | None = None

    def reset_health(self) -> None:
        """Reset transient health/cooldown state (used cleanly in automated tests)."""
        self._consecutive_failures = 0
        self._degraded_until_monotonic = None
        self._last_error_reason = None
        self._last_error_at = None
        self._last_active_model = None
        self._last_model_failover = None

    @staticmethod
    def _record_usage_db(
        scope_key: str, *, used_gemini: bool, used_fallback: bool, failed: bool
    ) -> None:
        today_ist = get_app_today()
        try:
            stmt = (
                pg_insert(AIUsageDaily)
                .values(
                    usage_date=today_ist,
                    scope_key=scope_key,
                    gemini_requests=1 if used_gemini else 0,
                    fallback_requests=1 if used_fallback else 0,
                    failed_requests=1 if failed else 0,
                )
                .on_conflict_do_update(
                    constraint="uq_ai_usage_daily_scope",
                    set_={
                        "gemini_requests": AIUsageDaily.gemini_requests + (1 if used_gemini else 0),
                        "fallback_requests": AIUsageDaily.fallback_requests
                        + (1 if used_fallback else 0),
                        "failed_requests": AIUsageDaily.failed_requests + (1 if failed else 0),
                        "updated_at": datetime.now(UTC),
                    },
                )
            )
            db.session.execute(stmt)
            db.session.commit()
        except Exception:  # noqa: BLE001 - telemetry write must not crash user flow
            db.session.rollback()
            logger.exception("ai_usage_counter_failed", extra={"scope_key": scope_key})

    def _get_daily_counts(self, user_id: int | None = None) -> dict[str, Any]:
        today_ist = get_app_today()
        daily_limit = int(current_app.config.get("AI_DAILY_REQUEST_LIMIT", 200))
        user_daily_limit = int(current_app.config.get("AI_USER_DAILY_LIMIT", 50))

        global_row = db.session.execute(
            select(AIUsageDaily).where(
                AIUsageDaily.usage_date == today_ist,
                AIUsageDaily.scope_key == AIUsageDaily.GLOBAL_SCOPE,
            )
        ).scalar_one_or_none()
        global_used = int(global_row.gemini_requests) if global_row else 0
        global_fallback = int(global_row.fallback_requests) if global_row else 0
        global_failed = int(global_row.failed_requests) if global_row else 0

        user_used = 0
        if user_id is not None:
            user_row = db.session.execute(
                select(AIUsageDaily).where(
                    AIUsageDaily.usage_date == today_ist,
                    AIUsageDaily.scope_key == AIUsageDaily.user_scope(user_id),
                )
            ).scalar_one_or_none()
            user_used = int(user_row.gemini_requests) if user_row else 0

        return {
            "usage_date_ist": today_ist.isoformat(),
            "daily_limit": daily_limit,
            "global_used_today": global_used,
            "global_remaining_today": max(daily_limit - global_used, 0),
            "fallback_requests_today": global_fallback,
            "failed_requests_today": global_failed,
            "user_daily_limit": user_daily_limit,
            "user_used_today": user_used if user_id is not None else None,
            "user_remaining_today": max(user_daily_limit - user_used, 0)
            if user_id is not None
            else None,
        }

    def _mark_failure(self, reason: str) -> None:
        cooldown_secs = int(current_app.config.get("AI_RECOVERY_COOLDOWN_SECONDS", 60))
        self._consecutive_failures += 1
        self._last_error_reason = reason
        self._last_error_at = datetime.now(UTC).isoformat()
        self._last_active_model = None
        if reason in {"auth_error", "rate_limited", "timeout", "provider_error"}:
            self._degraded_until_monotonic = time.monotonic() + cooldown_secs

    def _mark_success(self) -> None:
        self._consecutive_failures = 0
        self._degraded_until_monotonic = None
        self._last_error_reason = None
        self._last_success_at = datetime.now(UTC).isoformat()

    def _check_gemini_eligibility(self, user_id: int | None) -> str | None:
        configured = str(current_app.config.get("AI_PROVIDER", "auto")).lower()
        if configured == "local_fallback":
            return "configured_local_fallback"
        if not current_app.config.get("GEMINI_ENABLED", True):
            return "gemini_disabled"
        if not str(current_app.config.get("GEMINI_API_KEY") or "").strip():
            return "missing_api_key"

        if self._degraded_until_monotonic is not None:
            now_mono = time.monotonic()
            if now_mono < self._degraded_until_monotonic:
                return "cooldown_recovery_wait"
            # Cooldown expired -> automatically allow a recovery probe to Gemini

        counts = self._get_daily_counts(user_id=user_id)
        if counts["global_used_today"] >= counts["daily_limit"]:
            return "daily_quota_exceeded"
        if (
            user_id is not None
            and counts["user_used_today"] is not None
            and counts["user_used_today"] >= counts["user_daily_limit"]
        ):
            return "user_daily_quota_exceeded"
        return None

    def _record_gemini_success(
        self,
        result: ProviderResult,
        *,
        user_id: int | None,
        primary_model: str,
        failover_note: str | None = None,
    ) -> None:
        self._mark_success()
        self._last_active_model = result.model
        self._last_model_failover = failover_note
        self._record_usage_db(
            AIUsageDaily.GLOBAL_SCOPE, used_gemini=True, used_fallback=False, failed=False
        )
        if user_id is not None:
            self._record_usage_db(
                AIUsageDaily.user_scope(user_id),
                used_gemini=True,
                used_fallback=False,
                failed=False,
            )
        extra: dict[str, Any] = {
            "provider": result.provider,
            "model": result.model,
            "latency_ms": result.latency_ms,
        }
        if failover_note:
            extra.update(
                {
                    "primary_model": primary_model,
                    "model_switched": True,
                    "reason": failover_note,
                }
            )
        logger.info("ai_generation_completed", extra=extra)

    def generate_response(
        self,
        *,
        system_instruction: str,
        prompt: str,
        fallback_context: dict[str, Any],
        user_id: int | None = None,
        temperature: float = 0.3,
    ) -> ProviderResult:
        """Execute AI generation using Gemini when healthy/within quota, else LocalFallback."""
        if fallback_context.get("security_blocked"):
            return self._fallback.generate(
                system_instruction=system_instruction,
                prompt=prompt,
                fallback_context={
                    **fallback_context,
                    "fallback_triggered": False,
                    "fallback_reason": "security_guardrail",
                },
                temperature=0.0,
            )

        skip_reason = self._check_gemini_eligibility(user_id=user_id)
        if skip_reason is not None:
            fallback_triggered = skip_reason != "configured_local_fallback"
            result = self._fallback.generate(
                system_instruction=system_instruction,
                prompt=prompt,
                fallback_context={
                    **fallback_context,
                    "fallback_triggered": fallback_triggered,
                    "fallback_reason": skip_reason,
                },
                temperature=0.0,
            )
            self._record_usage_db(
                AIUsageDaily.GLOBAL_SCOPE, used_gemini=False, used_fallback=True, failed=False
            )
            if user_id is not None:
                self._record_usage_db(
                    AIUsageDaily.user_scope(user_id),
                    used_gemini=False,
                    used_fallback=True,
                    failed=False,
                )
            return result

        primary_model = str(current_app.config.get("GEMINI_MODEL") or "gemini-3.8-flash").strip()
        alt_model = str(current_app.config.get("GEMINI_FALLBACK_MODEL") or "").strip()

        try:
            result = self._gemini.generate(
                system_instruction=system_instruction,
                prompt=prompt,
                fallback_context=fallback_context,
                temperature=temperature,
            )
            self._record_gemini_success(
                result, user_id=user_id, primary_model=primary_model, failover_note=None
            )
            return result
        except AIProviderError as primary_exc:
            active_exc = primary_exc
            if (
                alt_model
                and alt_model != primary_model
                and primary_exc.reason in {"rate_limited", "provider_error", "timeout"}
            ):
                logger.warning(
                    "gemini_model_failover_attempted",
                    extra={
                        "primary_model": primary_model,
                        "alternative_model": alt_model,
                        "reason": primary_exc.reason,
                    },
                )
                try:
                    result = self._gemini.generate(
                        system_instruction=system_instruction,
                        prompt=prompt,
                        fallback_context=fallback_context,
                        temperature=temperature,
                        model_override=alt_model,
                    )
                    failover_note = f"alternative_model:{alt_model}:{primary_exc.reason}"
                    result = ProviderResult(
                        text=result.text,
                        provider=result.provider,
                        mode=result.mode,
                        model=result.model,
                        fallback_used=False,
                        reason=failover_note,
                        latency_ms=result.latency_ms,
                        usage=result.usage,
                    )
                    self._record_gemini_success(
                        result,
                        user_id=user_id,
                        primary_model=primary_model,
                        failover_note=failover_note,
                    )
                    return result
                except AIProviderError as alt_exc:
                    active_exc = alt_exc

            self._mark_failure(active_exc.reason)
            logger.warning(
                "gemini_fallback_activated",
                extra={
                    "reason": active_exc.reason,
                    "model": alt_model or primary_model,
                    "consecutive_failures": self._consecutive_failures,
                },
            )
            result = self._fallback.generate(
                system_instruction=system_instruction,
                prompt=prompt,
                fallback_context={
                    **fallback_context,
                    "fallback_triggered": True,
                    "fallback_reason": active_exc.reason,
                },
                temperature=0.0,
            )
            self._record_usage_db(
                AIUsageDaily.GLOBAL_SCOPE, used_gemini=False, used_fallback=True, failed=True
            )
            if user_id is not None:
                self._record_usage_db(
                    AIUsageDaily.user_scope(user_id),
                    used_gemini=False,
                    used_fallback=True,
                    failed=True,
                )
            return result

    def get_status(self, user_id: int | None = None) -> dict[str, Any]:
        """Return safe non-secret telemetry for passenger and admin status checks."""
        configured = str(current_app.config.get("AI_PROVIDER", "auto")).lower()
        gemini_enabled = bool(current_app.config.get("GEMINI_ENABLED", True))
        gemini_configured = bool(str(current_app.config.get("GEMINI_API_KEY") or "").strip())
        quota = self._get_daily_counts(user_id=user_id)

        cooldown_remaining = 0
        degraded = False
        if self._degraded_until_monotonic is not None:
            remaining = self._degraded_until_monotonic - time.monotonic()
            if remaining > 0:
                cooldown_remaining = max(1, math.ceil(remaining))
                degraded = True
            else:
                # Cooldown period elapsed; ready to probe Gemini automatically on next turn
                self._degraded_until_monotonic = None

        skip_reason = self._check_gemini_eligibility(user_id=user_id)
        active_provider = "gemini" if skip_reason is None else "local_fallback"
        active_mode = active_provider
        primary_model = str(current_app.config.get("GEMINI_MODEL", "gemini-3.8-flash")).strip()
        alt_model = str(current_app.config.get("GEMINI_FALLBACK_MODEL") or "").strip() or None
        reported_model = (
            self._last_active_model or primary_model
            if active_provider == "gemini"
            else "deterministic-local-v1"
        )

        return {
            "active_provider": active_provider,
            "mode": active_mode,
            "configured_provider": configured,
            "model": reported_model,
            "primary_model": primary_model,
            "alternative_model": alt_model,
            "last_model_failover": self._last_model_failover,
            "gemini_enabled": gemini_enabled,
            "gemini_configured": gemini_configured,
            "healthy": active_provider == "gemini" and not degraded,
            "degraded": degraded
            or (gemini_enabled and gemini_configured and active_provider != "gemini"),
            "fallback_reason": skip_reason,
            "cooldown_remaining_seconds": cooldown_remaining,
            "consecutive_failures": self._consecutive_failures,
            "last_error_reason": self._last_error_reason,
            "last_error_at": self._last_error_at,
            "last_success_at": self._last_success_at,
            "quota": quota,
            "features": {
                "passenger_assistant": True,
                "smart_recommendations": True,
                "admin_analytics_copilot": True,
                "conversation_retention": True,
            },
        }


_default_manager = AIProviderManager()


def get_ai_manager() -> AIProviderManager:
    """Return the active AIProviderManager attached to current Flask app or shared default."""
    manager = current_app.extensions.get("busreserve_ai_manager") if current_app else None
    if manager is None:
        return _default_manager
    return manager
