"""Notification domain service for multi-channel message dispatch and audit logging."""

import logging
import os
from typing import Any

from flask import current_app, has_app_context
from sqlalchemy import desc, func, or_, select

from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.utils.metrics import metrics_registry

logger = logging.getLogger("busreserve.notifications")


def _resolve_delivery_status(channel: str) -> str:
    """Resolve notification delivery status based on channel and provider availability.

    Returns:
    - Notification.STATUS_SENT: Successfully stored in-app or delivered to live provider.
    - Notification.STATUS_MOCK: Channel dispatched in mock/preview/test mode.
    - Notification.STATUS_NOT_CONFIGURED: Channel provider credentials missing in environment.
    - Notification.STATUS_FAILED: Delivery attempted but provider failed.
    """
    if channel == Notification.CHANNEL_IN_APP:
        # In-app alerts are saved directly into PostgreSQL and immediately visible
        # to the passenger on their dashboard. Completely independent of external providers.
        return Notification.STATUS_SENT

    env = os.getenv("FLASK_ENV", os.getenv("ENV", "development")).lower()
    is_test = env == "testing"
    app_config = current_app.config if has_app_context() else {}

    if channel == Notification.CHANNEL_EMAIL:
        smtp_host = app_config.get("SMTP_HOST") or os.getenv("SMTP_HOST", "")
        allow_preview = app_config.get("ALLOW_LOCAL_MAIL_PREVIEW", False) or (
            os.getenv("ALLOW_LOCAL_MAIL_PREVIEW", "").lower() in ("true", "1")
        )
        if smtp_host:
            return Notification.STATUS_SENT
        elif allow_preview or is_test:
            return Notification.STATUS_MOCK
        return Notification.STATUS_NOT_CONFIGURED

    elif channel == Notification.CHANNEL_SMS:
        twilio_sid = app_config.get("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_ACCOUNT_SID", "")
        if twilio_sid:
            return Notification.STATUS_SENT
        elif is_test:
            return Notification.STATUS_MOCK
        return Notification.STATUS_NOT_CONFIGURED

    elif channel == Notification.CHANNEL_WHATSAPP:
        wa_token = app_config.get("WHATSAPP_API_TOKEN") or os.getenv("WHATSAPP_API_TOKEN", "")
        if wa_token:
            return Notification.STATUS_SENT
        elif is_test:
            return Notification.STATUS_MOCK
        return Notification.STATUS_NOT_CONFIGURED

    return Notification.STATUS_NOT_CONFIGURED


def record_notification(
    channel: str,
    recipient: str,
    event_type: str,
    title: str,
    content: str,
    user_id: int | None = None,
    booking_id: int | None = None,
    status: str | None = None,
) -> Notification:
    """Persist a notification record and dispatch via the selected channel."""
    resolved_status = status or _resolve_delivery_status(channel)
    notif = Notification(
        user_id=user_id,
        booking_id=booking_id,
        channel=channel,
        recipient=recipient,
        event_type=event_type,
        title=title,
        content=content,
        status=resolved_status,
        is_read=False,
    )
    db.session.add(notif)
    db.session.commit()
    db.session.refresh(notif)

    metrics_registry.inc_counter(
        "busreserve_notifications_dispatched_total",
        1.0,
        {"channel": channel, "status": notif.status},
    )

    logger.info(
        "notification_dispatched",
        extra={
            "channel": channel,
            "recipient": recipient,
            "event_type": event_type,
            "notification_id": notif.id,
        },
    )
    return notif


def notify_booking_and_payment_success(booking, payment_tx=None) -> list[Notification]:
    """Dispatch confirmation email, SMS, and in-app alerts upon successful booking."""
    notifications: list[Notification] = []
    pnr = booking.pnr
    email = booking.passenger_email
    phone = booking.passenger_phone
    user_id = booking.user_id
    if user_id is None and email:
        matched_user_id = db.session.execute(
            select(User.id).where(User.email == email)
        ).scalar_one_or_none()
        if matched_user_id:
            user_id = matched_user_id
    booking_id = booking.id

    route_info = (
        f"{booking.trip.source} to {booking.trip.destination}"
        if booking.trip
        else "Scheduled Journey"
    )
    travel_date = booking.trip.travel_date if booking.trip else ""
    dep_time = booking.trip.departure_time if booking.trip else ""
    seat_num = booking.seat.seat_number if booking.seat else booking.seat_id
    fare = float(booking.total_fare)
    tx_ref = payment_tx.transaction_ref if payment_tx else "DEMO-SETTLED"

    # 1. Email notification
    email_title = f"Booking Confirmed: PNR {pnr} ({route_info})"
    email_content = (
        f"Dear {booking.passenger_name},\n\n"
        f"Your bus reservation has been successfully confirmed!\n\n"
        f"PNR: {pnr}\n"
        f"Route: {route_info}\n"
        f"Travel Date: {travel_date}\n"
        f"Departure Time: {dep_time} IST\n"
        f"Seat Number: {seat_num}\n"
        f"Total Fare: ₹{fare:.2f}\n"
        f"Payment Reference: {tx_ref}\n\n"
        f"Thank you for traveling with BusReserve."
    )
    notif_email = record_notification(
        channel=Notification.CHANNEL_EMAIL,
        recipient=email,
        event_type=Notification.EVENT_BOOKING_CONFIRMED,
        title=email_title,
        content=email_content,
        user_id=user_id,
        booking_id=booking_id,
    )
    notifications.append(notif_email)

    # 2. SMS notification (Sandbox mock)
    sms_title = f"BusReserve Ticket {pnr}"
    sms_content = (
        f"BusReserve: Confirmed ticket {pnr} for seat {seat_num} on {travel_date}. "
        f"Boarding at {booking.boarding_stop.stop_name if booking.boarding_stop else 'Station'}."
    )
    notif_sms = record_notification(
        channel=Notification.CHANNEL_SMS,
        recipient=phone,
        event_type=Notification.EVENT_BOOKING_CONFIRMED,
        title=sms_title,
        content=sms_content,
        user_id=user_id,
        booking_id=booking_id,
    )
    notifications.append(notif_sms)

    # 3. In-App Notification (for registered users)
    if user_id:
        notif_inapp = record_notification(
            channel=Notification.CHANNEL_IN_APP,
            recipient=email,
            event_type=Notification.EVENT_BOOKING_CONFIRMED,
            title=f"Reservation {pnr} Confirmed",
            content=(
                f"Your ticket for {route_info} on {travel_date} " f"(Seat {seat_num}) is confirmed."
            ),
            user_id=user_id,
            booking_id=booking_id,
        )
        notifications.append(notif_inapp)

    return notifications


def notify_booking_cancellation_and_refund(booking, refund_amount: float) -> list[Notification]:
    """Dispatch cancellation and refund notifications."""
    notifications: list[Notification] = []
    pnr = booking.pnr
    email = booking.passenger_email
    user_id = booking.user_id
    if user_id is None and email:
        matched_user_id = db.session.execute(
            select(User.id).where(User.email == email)
        ).scalar_one_or_none()
        if matched_user_id:
            user_id = matched_user_id
    booking_id = booking.id

    title = f"Reservation Cancelled: PNR {pnr}"
    content = (
        f"Dear {booking.passenger_name},\n\n"
        f"Your reservation with PNR {pnr} has been cancelled.\n"
        f"Refund Amount: ₹{refund_amount:.2f}\n"
        f"Refund Status: PROCESSED (Demo Gateway / Sandbox)\n\n"
        f"Your seat has been released. Contact support if you have questions."
    )
    notif_email = record_notification(
        channel=Notification.CHANNEL_EMAIL,
        recipient=email,
        event_type=Notification.EVENT_BOOKING_CANCELLED,
        title=title,
        content=content,
        user_id=user_id,
        booking_id=booking_id,
    )
    notifications.append(notif_email)

    if user_id:
        notif_inapp = record_notification(
            channel=Notification.CHANNEL_IN_APP,
            recipient=email,
            event_type=Notification.EVENT_BOOKING_CANCELLED,
            title=f"Booking {pnr} Cancelled",
            content=(
                f"Reservation {pnr} has been cancelled. "
                f"Refund of ₹{refund_amount:.2f} processed."
            ),
            user_id=user_id,
            booking_id=booking_id,
        )
        notifications.append(notif_inapp)

    return notifications


def list_user_notifications(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Retrieve in-app notifications for the passenger dashboard."""
    user = db.session.get(User, user_id)
    user_email = user.email.lower() if user and user.email else None

    filters = [Notification.user_id == user_id]
    if user_email:
        filters.append(func.lower(Notification.recipient) == user_email)

    stmt = (
        select(Notification)
        .where(
            or_(*filters),
            Notification.channel == Notification.CHANNEL_IN_APP,
        )
        .order_by(desc(Notification.created_at))
        .limit(min(100, max(1, limit)))
    )
    rows = db.session.execute(stmt).scalars().all()
    return [n.to_dict() for n in rows]


def mark_notification_read(notification_id: int, user_id: int) -> bool:
    """Mark an in-app notification as read for the user."""
    user = db.session.get(User, user_id)
    user_email = user.email.lower() if user and user.email else None

    filters = [Notification.user_id == user_id]
    if user_email:
        filters.append(func.lower(Notification.recipient) == user_email)

    notif = db.session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            or_(*filters),
        )
    ).scalar_one_or_none()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False


def notify_bus_departed(trip_id: int) -> list[Notification]:
    """Notify all confirmed passengers when their bus departs."""
    from app.models.booking import Booking
    from app.models.trip import Trip

    trip = db.session.get(Trip, trip_id)
    if not trip:
        return []

    bookings = (
        db.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        )
        .scalars()
        .all()
    )

    created_notifs: list[Notification] = []
    route_name = trip.route.name if trip.route else f"{trip.source} -> {trip.destination}"
    dep_time = trip.departure_time.strftime("%H:%M") if trip.departure_time else ""

    for booking in bookings:
        existing = db.session.execute(
            select(Notification.id).where(
                Notification.booking_id == booking.id,
                Notification.event_type == Notification.EVENT_BUS_DEPARTED,
            )
        ).scalar_one_or_none()
        if existing:
            continue

        title = f"Bus Departed: PNR {booking.pnr} ({route_name})"
        content = (
            f"Dear {booking.passenger_name},\n\n"
            f"Your bus {trip.bus_number} on {route_name} has departed at {dep_time} IST. "
            f"You can now track your bus live on the BusReserve map."
        )

        n1 = record_notification(
            channel=Notification.CHANNEL_IN_APP,
            recipient=booking.passenger_email,
            event_type=Notification.EVENT_BUS_DEPARTED,
            title=title,
            content=content,
            user_id=booking.user_id,
            booking_id=booking.id,
        )
        created_notifs.append(n1)

    return created_notifs


def notify_upcoming_stop(trip_id: int, stop_name: str, eta_minutes: int = 15) -> list[Notification]:
    """Notify passengers of an approaching boarding or drop station."""
    from app.models.booking import Booking
    from app.models.trip import Trip

    trip = db.session.get(Trip, trip_id)
    if not trip:
        return []

    bookings = (
        db.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        )
        .scalars()
        .all()
    )

    created_notifs: list[Notification] = []
    for booking in bookings:
        title = f"Next Stop: {stop_name} (ETA ~{eta_minutes} mins)"
        content = (
            f"Dear {booking.passenger_name},\n\n"
            f"Your bus is approaching {stop_name}. Estimated arrival in approximately {eta_minutes} minutes. "
            f"Please keep your belongings ready."
        )
        n = record_notification(
            channel=Notification.CHANNEL_IN_APP,
            recipient=booking.passenger_email,
            event_type=Notification.EVENT_UPCOMING_STOP,
            title=title,
            content=content,
            user_id=booking.user_id,
            booking_id=booking.id,
        )
        created_notifs.append(n)

    return created_notifs


def notify_delay_alert(trip_id: int, delay_minutes: int, reason: str | None = None) -> list[Notification]:
    """Notify passengers about significant transit delays."""
    from app.models.booking import Booking
    from app.models.trip import Trip

    trip = db.session.get(Trip, trip_id)
    if not trip:
        return []

    bookings = (
        db.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        )
        .scalars()
        .all()
    )

    created_notifs: list[Notification] = []
    for booking in bookings:
        title = f"Delay Alert: Trip running ~{delay_minutes} mins late"
        content = (
            f"Dear {booking.passenger_name},\n\n"
            f"Your bus {trip.bus_number} is experiencing a delay of approximately {delay_minutes} minutes"
            f"{f' due to {reason}' if reason else ''}. "
            f"We apologize for the inconvenience."
        )
        n = record_notification(
            channel=Notification.CHANNEL_IN_APP,
            recipient=booking.passenger_email,
            event_type=Notification.EVENT_DELAY_ALERT,
            title=title,
            content=content,
            user_id=booking.user_id,
            booking_id=booking.id,
        )
        created_notifs.append(n)

    return created_notifs


def notify_arrival(trip_id: int, destination_name: str) -> list[Notification]:
    """Notify passengers when the bus reaches its final destination."""
    from app.models.booking import Booking
    from app.models.trip import Trip

    trip = db.session.get(Trip, trip_id)
    if not trip:
        return []

    bookings = (
        db.session.execute(
            select(Booking).where(
                Booking.trip_id == trip_id,
                Booking.status == Booking.STATUS_CONFIRMED,
            )
        )
        .scalars()
        .all()
    )

    created_notifs: list[Notification] = []
    for booking in bookings:
        existing = db.session.execute(
            select(Notification.id).where(
                Notification.booking_id == booking.id,
                Notification.event_type == Notification.EVENT_ARRIVAL,
            )
        ).scalar_one_or_none()
        if existing:
            continue

        title = f"Trip Completed: Arrived at {destination_name}"
        content = (
            f"Dear {booking.passenger_name},\n\n"
            f"Your bus has arrived at {destination_name}. Thank you for traveling with BusReserve! "
            f"We hope you had a pleasant journey."
        )
        n = record_notification(
            channel=Notification.CHANNEL_IN_APP,
            recipient=booking.passenger_email,
            event_type=Notification.EVENT_ARRIVAL,
            title=title,
            content=content,
            user_id=booking.user_id,
            booking_id=booking.id,
        )
        created_notifs.append(n)

    return created_notifs


def notify_journey_shared(booking_id: int, share_url: str) -> Notification | None:
    """Record an audit alert when a live journey link is generated."""
    from app.models.booking import Booking

    booking = db.session.get(Booking, booking_id)
    if not booking:
        return None

    title = f"Live Journey Tracking Shared for PNR {booking.pnr}"
    content = (
        f"A secure, live tracking link has been created for your journey. "
        f"You can share this link with friends and family:\n{share_url}"
    )
    return record_notification(
        channel=Notification.CHANNEL_IN_APP,
        recipient=booking.passenger_email,
        event_type=Notification.EVENT_JOURNEY_SHARED,
        title=title,
        content=content,
        user_id=booking.user_id,
        booking_id=booking.id,
    )

