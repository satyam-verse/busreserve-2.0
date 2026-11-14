"""Pure-Python high-resolution PDF boarding pass and ticket generator."""

from datetime import UTC, datetime


def generate_ticket_pdf(booking) -> bytes:
    """Generate a valid A4 PDF 1.4 document for the passenger reservation ticket."""
    pnr = booking.pnr
    name = booking.passenger_name
    email = booking.passenger_email
    phone = booking.passenger_phone
    seat = booking.seat.seat_number if booking.seat else str(booking.seat_id)
    seat_type = booking.seat.seat_type if booking.seat else "STANDARD"
    fare = float(booking.total_fare)
    status = booking.status

    trip = booking.trip
    source = getattr(trip, "source", None) or "Source"
    dest = getattr(trip, "destination", None) or "Destination"
    operator = getattr(trip, "operator_name", "Express Lines")
    bus_num = getattr(trip, "bus_number", "N/A")
    raw_date = getattr(trip, "travel_date", "N/A")
    travel_date = raw_date.strftime("%Y-%m-%d") if hasattr(raw_date, "strftime") else str(raw_date)
    raw_dep = getattr(trip, "departure_time", "00:00")
    dep_time = raw_dep.strftime("%H:%M") if hasattr(raw_dep, "strftime") else str(raw_dep)
    raw_arr = getattr(trip, "arrival_time", "00:00")
    arr_time = raw_arr.strftime("%H:%M") if hasattr(raw_arr, "strftime") else str(raw_arr)

    b_stop = booking.boarding_stop.stop_name if booking.boarding_stop else "Boarding Point"
    d_stop = booking.drop_stop.stop_name if booking.drop_stop else "Dropping Point"

    tx = booking.payment_transactions[0] if booking.payment_transactions else None
    tx_ref = tx.transaction_ref if tx else "DEMO-PAYMENT-SETTLED"
    gateway = tx.gateway if tx else "MOCK_SANDBOX"

    # Assemble PDF stream content using PDF text and graphics operators
    stream_lines = [
        "q",
        # Navy header background
        "0.05 0.10 0.22 rg",
        "0 740 595 102 re",
        "f",
        # Emerald accent line
        "0.05 0.58 0.41 rg",
        "0 736 595 4 re",
        "f",
        # Header text
        "BT",
        "/F2 20 Tf",
        "1 1 1 rg",
        "40 790 Td",
        "(BUSRESERVE 2.0  -  OFFICIAL E-TICKET) Tj",
        "ET",
        "BT",
        "/F1 10 Tf",
        "0.8 0.85 0.9 rg",
        "40 765 Td",
        "(PREMIUM CLOUD-NATIVE INTERCITY BUS PLATFORM) Tj",
        "ET",
        # PNR & Status Banner Box
        "q",
        "0.96 0.96 0.98 rg",
        "40 650 515 65 re",
        "f",
        "0.80 0.82 0.88 RG",
        "1 w",
        "40 650 515 65 re",
        "S",
        "BT",
        "/F1 9 Tf",
        "0.4 0.45 0.55 rg",
        "55 695 Td",
        "(RESERVATION PNR CODE) Tj",
        "ET",
        "BT",
        "/F3 22 Tf",
        "0.05 0.10 0.22 rg",
        "55 665 Td",
        f"({pnr}) Tj",
        "ET",
        "BT",
        "/F1 9 Tf",
        "0.4 0.45 0.55 rg",
        "400 695 Td",
        "(BOOKING STATUS) Tj",
        "ET",
        "BT",
        "/F2 14 Tf",
        "0.05 0.58 0.41 rg" if status == "CONFIRMED" else "0.85 0.2 0.2 rg",
        "400 670 Td",
        f"({status}) Tj",
        "ET",
        "Q",
        # Journey Details Section
        "BT",
        "/F2 13 Tf",
        "0.05 0.10 0.22 rg",
        "40 615 Td",
        "(JOURNEY & SCHEDULE) Tj",
        "ET",
        "0.85 0.87 0.90 RG",
        "1 w",
        "40 605 m 555 605 l S",
        "BT",
        "/F2 16 Tf",
        "0.05 0.10 0.22 rg",
        "40 580 Td",
        f"({source}   >>>   {dest}) Tj",
        "ET",
        "BT",
        "/F1 10 Tf",
        "0.3 0.35 0.4 rg",
        "40 555 Td",
        f"(Operator: {operator}    |    Bus: {bus_num}) Tj",
        "40 535 Td",
        f"(Travel Date: {travel_date}    |    Time: {dep_time} - {arr_time} IST) Tj",
        "40 515 Td",
        f"(Boarding Stop: {b_stop}) Tj",
        "40 495 Td",
        f"(Dropping Stop: {d_stop}) Tj",
        "ET",
        # Passenger & Seat Section
        "BT",
        "/F2 13 Tf",
        "0.05 0.10 0.22 rg",
        "40 455 Td",
        "(PASSENGER & SEAT ASSIGNMENT) Tj",
        "ET",
        "0.85 0.87 0.90 RG",
        "1 w",
        "40 445 m 555 445 l S",
        "BT",
        "/F1 10 Tf",
        "0.3 0.35 0.4 rg",
        "40 420 Td",
        f"(Passenger Name: {name}) Tj",
        "40 400 Td",
        f"(Contact Email: {email}) Tj",
        "40 380 Td",
        f"(Contact Phone: {phone}) Tj",
        "40 360 Td",
        f"(Seat Assigned: {seat} [{seat_type}]) Tj",
        "ET",
        # Payment & Financial Receipt Section
        "BT",
        "/F2 13 Tf",
        "0.05 0.10 0.22 rg",
        "40 320 Td",
        "(PAYMENT & TRANSACTION RECEIPT) Tj",
        "ET",
        "0.85 0.87 0.90 RG",
        "1 w",
        "40 310 m 555 310 l S",
        "BT",
        "/F1 10 Tf",
        "0.3 0.35 0.4 rg",
        "40 285 Td",
        f"(Total Fare Paid: INR {fare:.2f}) Tj",
        "40 265 Td",
        f"(Transaction Ref: {tx_ref}) Tj",
        "40 245 Td",
        f"(Payment Gateway: {gateway}) Tj",
        "40 225 Td",
        "(Settlement Status: VERIFIED & CONFIRMED) Tj",
        "ET",
        # Security & Verification Notice
        "q",
        "0.97 0.97 0.97 rg",
        "40 100 515 85 re",
        "f",
        "0.88 0.88 0.90 RG",
        "1 w",
        "40 100 515 85 re",
        "S",
        "BT",
        "/F2 9 Tf",
        "0.2 0.2 0.25 rg",
        "50 165 Td",
        "(IMPORTANT TRAVEL INSTRUCTIONS & VERIFICATION) Tj",
        "ET",
        "BT",
        "/F1 8 Tf",
        "0.4 0.45 0.5 rg",
        "50 148 Td",
        "(1. Present this electronic ticket along with a valid photo ID at boarding.) Tj",
        "50 133 Td",
        "(2. Report to your boarding point at least 15 minutes before departure.) Tj",
        "50 118 Td",
        "(3. For ticket cancellation and refunds, visit /bookings with your PNR.) Tj",
        "ET",
        "Q",
        # Footer
        "BT",
        "/F1 8 Tf",
        "0.6 0.65 0.7 rg",
        "190 40 Td",
        f"(Generated by BusReserve Core - {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}) Tj",
        "ET",
        "Q",
    ]

    stream_content = "\n".join(stream_lines).encode("latin-1")
    stream_len = len(stream_content)

    objects = [
        # Obj 1: Catalog
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        # Obj 2: Pages
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        # Obj 3: Page (A4: 595 x 842 points)
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 4 0 R /Resources << /Font << "
            b"/F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> >>\nendobj\n"
        ),
        # Obj 4: Content stream
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii")
        + stream_content
        + b"\nendstream\nendobj\n",
        # Obj 5: Helvetica
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        # Obj 6: Helvetica-Bold
        b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n",
        # Obj 7: Courier-Bold
        b"7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>\nendobj\n",
    ]

    # Build PDF with xref table
    pdf_parts = [b"%PDF-1.4\n"]
    offsets = []
    current_offset = len(pdf_parts[0])

    for obj in objects:
        offsets.append(current_offset)
        pdf_parts.append(obj)
        current_offset += len(obj)

    xref_offset = current_offset
    pdf_parts.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets:
        pdf_parts.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer_str = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    pdf_parts.append(trailer_str.encode("ascii"))

    return b"".join(pdf_parts)
