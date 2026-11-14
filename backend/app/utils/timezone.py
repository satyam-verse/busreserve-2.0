"""Consistent application timezone helpers standardized to Asia/Kolkata (IST)."""

import os
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import has_app_context

DEFAULT_APP_TIMEZONE = "Asia/Kolkata"
_IST_FALLBACK = timezone(timedelta(hours=5, minutes=30), name="IST")


def get_app_timezone_name() -> str:
    """Resolve the configured application timezone name."""
    if has_app_context():
        from flask import current_app

        configured = current_app.config.get("APP_TIMEZONE")
        if configured:
            return str(configured)
    return os.getenv("APP_TIMEZONE", DEFAULT_APP_TIMEZONE)


def get_app_timezone(tz_name: str | None = None) -> tzinfo:
    """Return the tzinfo object for APP_TIMEZONE (defaults to Asia/Kolkata)."""
    target_name = tz_name or get_app_timezone_name()
    try:
        return ZoneInfo(target_name)
    except ZoneInfoNotFoundError:
        if target_name in ("Asia/Kolkata", "Asia/Calcutta", "IST"):
            return _IST_FALLBACK
        raise


def get_utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(UTC)


def get_app_now(tz_name: str | None = None) -> datetime:
    """Return current datetime converted to APP_TIMEZONE (Asia/Kolkata)."""
    return get_utc_now().astimezone(get_app_timezone(tz_name))


def get_app_today(tz_name: str | None = None) -> date:
    """Return the current calendar date in APP_TIMEZONE (Asia/Kolkata)."""
    return get_app_now(tz_name).date()
