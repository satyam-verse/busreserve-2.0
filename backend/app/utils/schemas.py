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
        if len(value) < 2 or len(value) > 120:
            raise ValidationError("Passenger name must be between 2 and 120 characters.")
        if not any(ch.isalpha() for ch in value):
            raise ValidationError("Passenger name must contain alphabetic characters.")
        if not re.match(r"^[A-Za-z\u00C0-\u024F\s.'\-]+$", value):
            raise ValidationError("Passenger name contains invalid characters.")

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
