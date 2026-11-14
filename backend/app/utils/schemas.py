"""Marshmallow schemas for validating API inputs."""

import re

from marshmallow import (
    Schema,
    ValidationError,
    fields,
    pre_load,
    validate,
    validates,
    validates_schema,
)

PHONE_PATTERN = re.compile(r"^(\+?[1-9]\d{9,14}|0[6-9]\d{9}|[6-9]\d{9})$")


def _validate_strong_password(value: str) -> None:
    if len(value) < 8 or len(value) > 128:
        raise ValidationError("Password must be between 8 and 128 characters.")
    if not any(ch.isupper() for ch in value):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not any(ch.islower() for ch in value):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not any(ch.isdigit() for ch in value):
        raise ValidationError("Password must contain at least one digit.")


def _validate_person_name(value: str) -> None:
    if len(value) < 2 or len(value) > 120:
        raise ValidationError("Name must be between 2 and 120 characters.")
    if not any(ch.isalpha() for ch in value):
        raise ValidationError("Name must contain alphabetic characters.")
    if not re.match(r"^[A-Za-z\u00C0-\u024F\s.'\-]+$", value):
        raise ValidationError("Name contains invalid characters.")


class CitySearchSchema(Schema):
    """Query parameter schema for dynamic Indian city autocomplete."""

    q = fields.Str(load_default=None, validate=validate.Length(max=100))
    limit = fields.Int(load_default=15, validate=validate.Range(min=1, max=100))

    @pre_load
    def _normalize_city_query(self, data: dict, **kwargs) -> dict:
        cleaned = dict(data)
        if "q" in cleaned and isinstance(cleaned["q"], str):
            cleaned["q"] = cleaned["q"].strip()
            if cleaned["q"] == "":
                cleaned.pop("q")
        return cleaned


class TripSearchSchema(Schema):
    """Query parameter schema for searching scheduled bus trips."""

    source = fields.Str(load_default=None, validate=validate.Length(max=100))
    destination = fields.Str(load_default=None, validate=validate.Length(max=100))
    travel_date = fields.Date(load_default=None)
    sort_by = fields.Str(
        load_default="departure_asc",
        validate=validate.OneOf(["departure_asc", "fare_asc", "fare_desc", "seats_desc"]),
    )
    min_seats = fields.Int(load_default=None, validate=validate.Range(min=1, max=100))
    featured = fields.Bool(load_default=False)

    @pre_load
    def _normalize_query(self, data: dict, **kwargs) -> dict:
        cleaned = dict(data)
        for key in ("source", "destination", "travel_date", "min_seats", "sort_by"):
            if key in cleaned and isinstance(cleaned[key], str) and cleaned[key].strip() == "":
                cleaned.pop(key)
        return cleaned


class BookingCreateSchema(Schema):
    """Request payload schema for reserving a seat on a bus trip."""

    trip_id = fields.Int(required=True, strict=False, validate=validate.Range(min=1))
    seat_number = fields.Str(load_default=None, validate=validate.Length(min=1, max=10))
    seat_id = fields.Int(load_default=None, strict=False, validate=validate.Range(min=1))
    travel_date = fields.Date(load_default=None)
    passenger_name = fields.Str(required=True)
    passenger_email = fields.Email(required=True, validate=validate.Length(max=160))
    passenger_phone = fields.Str(required=True)
    boarding_stop_id = fields.Int(required=True, strict=False, validate=validate.Range(min=1))
    drop_stop_id = fields.Int(required=True, strict=False, validate=validate.Range(min=1))

    @pre_load
    def _strip_inputs(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for key in ("passenger_name", "passenger_email", "passenger_phone", "seat_number"):
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        if isinstance(cleaned.get("passenger_email"), str):
            cleaned["passenger_email"] = cleaned["passenger_email"].lower()
        if isinstance(cleaned.get("seat_number"), str):
            cleaned["seat_number"] = cleaned["seat_number"].upper()
        if isinstance(cleaned.get("passenger_phone"), str):
            cleaned["passenger_phone"] = re.sub(r"[\s\-()]", "", cleaned["passenger_phone"])
        return cleaned

    @validates("passenger_name")
    def _validate_passenger_name(self, value: str) -> None:
        _validate_person_name(value)

    @validates("passenger_phone")
    def _validate_passenger_phone(self, value: str) -> None:
        if not PHONE_PATTERN.match(value):
            raise ValidationError(
                "Provide a valid 10-digit mobile number or E.164 phone number (e.g. +919876543210)."
            )

    @validates_schema
    def _validate_cross_fields(self, data: dict, **kwargs) -> None:
        if not data.get("seat_number") and not data.get("seat_id"):
            raise ValidationError(
                {"seat_number": ["Either seat_number or seat_id must be provided."]}
            )
        if data["boarding_stop_id"] == data["drop_stop_id"]:
            raise ValidationError(
                {"drop_stop_id": ["Drop stop must be different from boarding stop."]}
            )


class RegisterSchema(Schema):
    """Customer registration payload schema."""

    full_name = fields.Str(required=True)
    email = fields.Email(required=True, validate=validate.Length(max=160))
    phone = fields.Str(load_default=None)
    password = fields.Str(required=True)

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for key in ("full_name", "email", "phone"):
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        if isinstance(cleaned.get("email"), str):
            cleaned["email"] = cleaned["email"].lower()
        if isinstance(cleaned.get("phone"), str):
            cleaned["phone"] = re.sub(r"[\s\-()]", "", cleaned["phone"]) or None
        return cleaned

    @validates("full_name")
    def _check_name(self, value: str) -> None:
        _validate_person_name(value)

    @validates("phone")
    def _check_phone(self, value: str | None) -> None:
        if value is not None and not PHONE_PATTERN.match(value):
            raise ValidationError("Provide a valid 10-digit mobile number or E.164 phone number.")

    @validates("password")
    def _check_password(self, value: str) -> None:
        _validate_strong_password(value)


class LoginSchema(Schema):
    """User or Admin login payload schema."""

    email = fields.Email(required=True, validate=validate.Length(max=160))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=128))

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if isinstance(cleaned.get("email"), str):
            cleaned["email"] = cleaned["email"].strip().lower()
        return cleaned


class VerifyEmailSchema(Schema):
    token = fields.Str(required=True, validate=validate.Length(min=10, max=256))


class EmailOnlySchema(Schema):
    email = fields.Email(required=True, validate=validate.Length(max=160))

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            cleaned = dict(data)
            cleaned["email"] = cleaned["email"].strip().lower()
            return cleaned
        return data


class ResetPasswordSchema(Schema):
    token = fields.Str(required=True, validate=validate.Length(min=10, max=256))
    new_password = fields.Str(required=True)

    @validates("new_password")
    def _check_password(self, value: str) -> None:
        _validate_strong_password(value)


class ProfileUpdateSchema(Schema):
    full_name = fields.Str()
    phone = fields.Str(allow_none=True)

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if isinstance(cleaned.get("full_name"), str):
            cleaned["full_name"] = cleaned["full_name"].strip()
        if isinstance(cleaned.get("phone"), str):
            cleaned["phone"] = re.sub(r"[\s\-()]", "", cleaned["phone"]) or None
        return cleaned

    @validates("full_name")
    def _check_name(self, value: str) -> None:
        _validate_person_name(value)

    @validates("phone")
    def _check_phone(self, value: str | None) -> None:
        if value is not None and not PHONE_PATTERN.match(value):
            raise ValidationError("Provide a valid 10-digit mobile number or E.164 phone number.")


class ChangePasswordSchema(Schema):
    current_password = fields.Str(required=True, validate=validate.Length(min=1, max=128))
    new_password = fields.Str(required=True)

    @validates("new_password")
    def _check_password(self, value: str) -> None:
        _validate_strong_password(value)


class AdminUserUpdateSchema(Schema):
    is_active = fields.Bool()
    email_verified = fields.Bool()
    role = fields.Str(validate=validate.OneOf(["USER", "ADMIN", "DRIVER", "OPERATOR"]))


class AdminCityCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    state = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    aliases = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=255))


class AdminCityUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=100))
    state = fields.Str(allow_none=True, validate=validate.Length(max=100))
    aliases = fields.Str(allow_none=True, validate=validate.Length(max=255))
    is_active = fields.Bool()


class AdminRouteCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=3, max=150))
    source = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    destination = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    distance_km = fields.Int(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=5000)
    )
    estimated_duration_minutes = fields.Int(
        load_default=None, allow_none=True, validate=validate.Range(min=10, max=4320)
    )
    stops = fields.List(
        fields.Str(validate=validate.Length(min=2, max=120)),
        required=True,
        validate=validate.Length(min=2, max=25),
    )

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for key in ("name", "source", "destination"):
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        if isinstance(cleaned.get("stops"), list):
            cleaned["stops"] = [s.strip() if isinstance(s, str) else s for s in cleaned["stops"]]
        return cleaned

    @validates_schema
    def _check_distinct(self, data: dict, **kwargs) -> None:
        if data["source"].strip().lower() == data["destination"].strip().lower():
            raise ValidationError({"destination": ["Destination must differ from source."]})
        lowered_stops = [s.strip().lower() for s in data["stops"]]
        if len(lowered_stops) != len(set(lowered_stops)):
            raise ValidationError({"stops": ["Route stops must be distinct."]})


class AdminRouteUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=3, max=150))
    source = fields.Str(validate=validate.Length(min=2, max=100))
    destination = fields.Str(validate=validate.Length(min=2, max=100))
    distance_km = fields.Int(allow_none=True, validate=validate.Range(min=1, max=5000))
    estimated_duration_minutes = fields.Int(
        allow_none=True, validate=validate.Range(min=10, max=4320)
    )
    stops = fields.List(
        fields.Str(validate=validate.Length(min=2, max=120)),
        validate=validate.Length(min=2, max=25),
    )

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for key in ("name", "source", "destination"):
            if isinstance(cleaned.get(key), str):
                cleaned[key] = cleaned[key].strip()
        if isinstance(cleaned.get("stops"), list):
            cleaned["stops"] = [s.strip() if isinstance(s, str) else s for s in cleaned["stops"]]
        return cleaned

    @validates_schema
    def _check_stops(self, data: dict, **kwargs) -> None:
        if "source" in data and "destination" in data:
            if data["source"].strip().lower() == data["destination"].strip().lower():
                raise ValidationError({"destination": ["Destination must differ from source."]})
        if "stops" in data:
            lowered_stops = [s.strip().lower() for s in data["stops"]]
            if len(lowered_stops) != len(set(lowered_stops)):
                raise ValidationError({"stops": ["Route stops must be distinct."]})


class AdminBusCreateSchema(Schema):
    operator_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    registration_number = fields.Str(required=True, validate=validate.Length(min=3, max=40))
    bus_type = fields.Str(
        load_default="AC_SEATER",
        validate=validate.OneOf(
            ["AC_SEATER", "NON_AC_SEATER", "AC_SLEEPER", "SEATER_SLEEPER", "VOLVO_MULTI_AXLE"]
        ),
    )
    seat_layout = fields.Str(load_default="2+2", validate=validate.OneOf(["2+2", "2+1", "1+2"]))
    total_seats = fields.Int(load_default=32, validate=validate.Range(min=4, max=80))
    amenities = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=255))
    is_active = fields.Bool(load_default=True)

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if isinstance(cleaned.get("operator_name"), str):
            cleaned["operator_name"] = cleaned["operator_name"].strip()
        if isinstance(cleaned.get("registration_number"), str):
            cleaned["registration_number"] = cleaned["registration_number"].strip().upper()
        if isinstance(cleaned.get("amenities"), str):
            cleaned["amenities"] = cleaned["amenities"].strip() or None
        return cleaned


class AdminBusUpdateSchema(Schema):
    operator_name = fields.Str(validate=validate.Length(min=2, max=120))
    registration_number = fields.Str(validate=validate.Length(min=3, max=40))
    bus_type = fields.Str(
        validate=validate.OneOf(
            ["AC_SEATER", "NON_AC_SEATER", "AC_SLEEPER", "SEATER_SLEEPER", "VOLVO_MULTI_AXLE"]
        )
    )
    seat_layout = fields.Str(validate=validate.OneOf(["2+2", "2+1", "1+2"]))
    total_seats = fields.Int(validate=validate.Range(min=4, max=80))
    amenities = fields.Str(allow_none=True, validate=validate.Length(max=255))
    is_active = fields.Bool()

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if isinstance(cleaned.get("operator_name"), str):
            cleaned["operator_name"] = cleaned["operator_name"].strip()
        if isinstance(cleaned.get("registration_number"), str):
            cleaned["registration_number"] = cleaned["registration_number"].strip().upper()
        if isinstance(cleaned.get("amenities"), str):
            cleaned["amenities"] = cleaned["amenities"].strip() or None
        return cleaned


class AdminScheduleCreateSchema(Schema):
    route_id = fields.Int(required=True, strict=False, validate=validate.Range(min=1))
    bus_id = fields.Int(
        load_default=None, allow_none=True, strict=False, validate=validate.Range(min=1)
    )
    operator_name = fields.Str(
        load_default=None, allow_none=True, validate=validate.Length(min=2, max=120)
    )
    bus_number = fields.Str(
        load_default=None, allow_none=True, validate=validate.Length(min=3, max=40)
    )
    bus_type = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(
            ["AC_SEATER", "NON_AC_SEATER", "AC_SLEEPER", "SEATER_SLEEPER", "VOLVO_MULTI_AXLE"]
        ),
    )
    seat_layout = fields.Str(
        load_default=None, allow_none=True, validate=validate.OneOf(["2+2", "2+1", "1+2"])
    )
    departure_time = fields.Time(required=True)
    arrival_time = fields.Time(required=True)
    base_fare = fields.Decimal(required=True, as_string=False, validate=validate.Range(min=1))
    seat_count = fields.Int(
        load_default=None, allow_none=True, validate=validate.Range(min=4, max=80)
    )
    horizon_days = fields.Int(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=365)
    )

    @validates_schema
    def _check_bus_source(self, data: dict, **kwargs) -> None:
        if not data.get("bus_id") and (not data.get("operator_name") or not data.get("bus_number")):
            raise ValidationError(
                {"bus_id": ["Provide bus_id or both operator_name and bus_number."]}
            )


class AdminScheduleUpdateSchema(Schema):
    bus_id = fields.Int(allow_none=True, strict=False, validate=validate.Range(min=1))
    departure_time = fields.Time()
    arrival_time = fields.Time()
    base_fare = fields.Decimal(as_string=False, validate=validate.Range(min=1))
    seat_count = fields.Int(validate=validate.Range(min=4, max=80))
    is_active = fields.Bool()
    apply_to_future_trips = fields.Bool(load_default=True)


class AdminBookingCancelSchema(Schema):
    reason = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=255))
    process_refund = fields.Bool(load_default=True)


class AdminBookingRefundSchema(Schema):
    amount = fields.Decimal(
        load_default=None, allow_none=True, as_string=False, validate=validate.Range(min=0)
    )
    note = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=255))


def _validate_ai_text_length(value: str) -> None:
    from flask import current_app, has_app_context

    max_len = (
        int(current_app.config.get("AI_MAX_INPUT_LENGTH", 1000)) if has_app_context() else 1000
    )
    clean = value.strip()
    if not clean:
        raise ValidationError("Message cannot be empty.")
    if len(clean) > max_len:
        raise ValidationError(f"Message exceeds maximum allowed length of {max_len} characters.")


class AIChatSchema(Schema):
    """Validation schema for Passenger AI assistant chat turns."""

    message = fields.Str(required=True)
    source = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    destination = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    travel_date = fields.Date(load_default=None, allow_none=True)
    max_budget = fields.Float(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=100000)
    )
    min_seats = fields.Int(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=40)
    )
    preference = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(
            ["cheapest", "earliest", "overnight", "shortest", "most_seats", "balanced"]
        ),
    )
    time_window = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["early_morning", "morning", "afternoon", "evening", "overnight"]),
    )
    bus_type = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=40))
    seat_preference = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["WINDOW", "AISLE"]),
    )

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if "message" not in cleaned and isinstance(cleaned.get("query"), str):
            cleaned["message"] = cleaned["query"]
        if isinstance(cleaned.get("message"), str):
            cleaned["message"] = cleaned["message"].strip()
        for key in (
            "source",
            "destination",
            "travel_date",
            "preference",
            "time_window",
            "bus_type",
            "seat_preference",
        ):
            if key in cleaned and isinstance(cleaned[key], str) and cleaned[key].strip() == "":
                cleaned[key] = None
        if isinstance(cleaned.get("seat_preference"), str):
            cleaned["seat_preference"] = cleaned["seat_preference"].strip().upper()
        if isinstance(cleaned.get("preference"), str):
            cleaned["preference"] = cleaned["preference"].strip().lower()
        if isinstance(cleaned.get("time_window"), str):
            cleaned["time_window"] = cleaned["time_window"].strip().lower()
        return cleaned

    @validates("message")
    def _check_message(self, value: str) -> None:
        _validate_ai_text_length(value)


class AIRecommendationSchema(Schema):
    """Validation schema for smart route & trip recommendation queries."""

    query = fields.Str(load_default="", allow_none=True)
    message = fields.Str(load_default="", allow_none=True)
    source = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    destination = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    travel_date = fields.Date(load_default=None, allow_none=True)
    max_budget = fields.Float(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=100000)
    )
    min_seats = fields.Int(
        load_default=None, allow_none=True, validate=validate.Range(min=1, max=40)
    )
    preference = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(
            ["cheapest", "earliest", "overnight", "shortest", "most_seats", "balanced"]
        ),
    )
    time_window = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["early_morning", "morning", "afternoon", "evening", "overnight"]),
    )
    bus_type = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=40))
    seat_preference = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.OneOf(["WINDOW", "AISLE"]),
    )
    limit = fields.Int(load_default=5, validate=validate.Range(min=1, max=10))

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        for key in (
            "query",
            "message",
            "source",
            "destination",
            "preference",
            "time_window",
            "bus_type",
            "seat_preference",
            "travel_date",
        ):
            if key in cleaned and isinstance(cleaned[key], str):
                cleaned[key] = cleaned[key].strip()
                if key not in ("query", "message") and cleaned[key] == "":
                    cleaned[key] = None
        if isinstance(cleaned.get("seat_preference"), str):
            cleaned["seat_preference"] = cleaned["seat_preference"].strip().upper()
        if isinstance(cleaned.get("preference"), str):
            cleaned["preference"] = cleaned["preference"].strip().lower()
        if isinstance(cleaned.get("time_window"), str):
            cleaned["time_window"] = cleaned["time_window"].strip().lower()
        return cleaned

    @validates_schema
    def _check_text_bounds(self, data: dict, **kwargs) -> None:
        from flask import current_app, has_app_context

        max_len = (
            int(current_app.config.get("AI_MAX_INPUT_LENGTH", 1000)) if has_app_context() else 1000
        )
        raw_text = (data.get("query") or data.get("message") or "").strip()
        if len(raw_text) > max_len:
            raise ValidationError(
                {"query": [f"Query exceeds maximum allowed length of {max_len} characters."]}
            )


class AdminAIChatSchema(Schema):
    """Validation schema for Admin Operations AI Copilot requests."""

    message = fields.Str(required=True)

    @pre_load
    def _normalize(self, data: dict, **kwargs) -> dict:
        if not isinstance(data, dict):
            return data
        cleaned = dict(data)
        if "message" not in cleaned and isinstance(cleaned.get("query"), str):
            cleaned["message"] = cleaned["query"]
        if isinstance(cleaned.get("message"), str):
            cleaned["message"] = cleaned["message"].strip()
        return cleaned

    @validates("message")
    def _check_message(self, value: str) -> None:
        _validate_ai_text_length(value)


class GPSPingSchema(Schema):
    """Validation schema for incoming Driver and Operator GPS coordinates."""

    trip_id = fields.Int(required=True, validate=validate.Range(min=1))
    sequence_number = fields.Int(required=True, validate=validate.Range(min=1))
    client_timestamp = fields.DateTime(required=True)
    latitude = fields.Float(required=True, validate=validate.Range(min=-90.0, max=90.0))
    longitude = fields.Float(required=True, validate=validate.Range(min=-180.0, max=180.0))
    accuracy = fields.Float(load_default=None, validate=validate.Range(min=0.0, max=5000.0))
    speed = fields.Float(load_default=None, validate=validate.Range(min=0.0, max=150.0))
    heading = fields.Float(load_default=None, validate=validate.Range(min=0.0, max=360.0))


class JourneyShareCreateSchema(Schema):
    """Validation schema for passenger creating a live journey tracking link."""

    booking_id = fields.Int(required=True, validate=validate.Range(min=1))
    validity_hours = fields.Int(load_default=24, validate=validate.Range(min=1, max=168))


class SeatFilterSchema(Schema):
    """Query parameter schema for filtering seats by tier, position, and fare."""

    tier = fields.Str(
        load_default=None,
        validate=validate.OneOf(["STANDARD", "PREMIUM", "SLEEPER"]),
    )
    position = fields.Str(
        load_default=None,
        validate=validate.OneOf(["FRONT", "MIDDLE", "BACK", "SINGLE"]),
    )
    max_fare = fields.Float(load_default=None, validate=validate.Range(min=0.0))
    available_only = fields.Bool(load_default=True)


class DriverAssignSchema(Schema):
    """Schema for assigning a driver to a trip."""

    driver_id = fields.Int(required=True, validate=validate.Range(min=1))
    trip_id = fields.Int(required=True, validate=validate.Range(min=1))

