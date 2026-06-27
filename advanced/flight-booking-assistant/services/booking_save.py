import os
import random
import sqlite3
import uuid
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "indigo_airline.db")


def _generate_pnr() -> str:
    letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    digits = random.randint(100000, 999999)
    return f"{letter}{digits}"


def _unique_pnr(cur) -> str:
    for _ in range(10):
        code = _generate_pnr()
        cur.execute("SELECT 1 FROM PNRs WHERE pnr_code = ?", (code,))
        if not cur.fetchone():
            return code
    raise RuntimeError("Could not generate a unique PNR after 10 attempts")


def save_booking(state: dict) -> dict:
    """
    Persist the completed booking to the database.
    Returns {"pnr_code": str, "transaction_id": str}.
    """
    adults = state.get("adults") or 1
    children = state.get("children") or 0
    total_passengers = adults + children
    trip_type = state.get("trip_type", "one-way")
    travel_date = state.get("travel_date", "")
    return_date = state.get("return_date", "")
    passengers = state.get("passengers") or []

    outbound = state.get("selected_outbound_flight") or state.get("selected_flight") or {}
    return_flight = state.get("selected_return_flight") or {}
    is_round_trip = bool(outbound and return_flight)

    outbound_price = outbound.get("price", 0)
    return_price = return_flight.get("price", 0) if is_round_trip else 0
    total_amount = (outbound_price + return_price) * adults

    now = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()

    try:
        valid_date = str(date.fromisoformat(travel_date) + timedelta(days=365))
    except Exception:
        valid_date = str(date.today() + timedelta(days=365))

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        pnr_code = _unique_pnr(cur)
        transaction_id = str(uuid.uuid4()).upper()[:16]

        cur.execute(
            """INSERT INTO PNRs (pnr_code, customer_id, pnr_status, issue_date, valid_until, created_at, updated_at)
               VALUES (?, NULL, 'issued', ?, ?, ?, ?)""",
            (pnr_code, today, valid_date, now, now),
        )

        booking_id = f"BK{uuid.uuid4().hex[:10].upper()}"
        outbound_flight_id = outbound.get("flight_number", "")
        cur.execute(
            """INSERT INTO Bookings
               (booking_id, pnr_code, customer_id, flight_id, flight_date,
                total_passengers, booking_status, booking_type,
                total_fare, tax_charges, discount, final_amount, created_at, updated_at)
               VALUES (?, ?, NULL, ?, ?, ?, 'confirmed', ?,
                       ?, 0, 0, ?, ?, ?)""",
            (
                booking_id, pnr_code, outbound_flight_id, travel_date,
                total_passengers, trip_type,
                outbound_price * adults, outbound_price * adults, now, now,
            ),
        )

        if is_round_trip:
            return_booking_id = f"BK{uuid.uuid4().hex[:10].upper()}"
            return_flight_id = return_flight.get("flight_number", "")
            cur.execute(
                """INSERT INTO Bookings
                   (booking_id, pnr_code, customer_id, flight_id, flight_date,
                    total_passengers, booking_status, booking_type,
                    total_fare, tax_charges, discount, final_amount, created_at, updated_at)
                   VALUES (?, ?, NULL, ?, ?, ?, 'confirmed', ?,
                           ?, 0, 0, ?, ?, ?)""",
                (
                    return_booking_id, pnr_code, return_flight_id, return_date,
                    total_passengers, trip_type,
                    return_price * adults, return_price * adults, now, now,
                ),
            )

        title_to_gender = {"Mr": "M", "Mrs": "F", "Miss": "F", "Master": "M"}
        category_to_type = {"adult": "Adult", "child": "Child", "infant": "Infant"}
        for p in passengers:
            passenger_id = f"PAX{uuid.uuid4().hex[:10].upper()}"
            gender = title_to_gender.get(p.get("title", ""), "M")
            ptype = category_to_type.get(p.get("age_category", "adult"), "Adult")
            cur.execute(
                """INSERT INTO Passengers
                   (passenger_id, booking_id, first_name, last_name,
                    gender, passenger_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    passenger_id, booking_id,
                    p.get("first_name", ""), p.get("last_name", ""),
                    gender, ptype, now,
                ),
            )

        payment_id = f"PAY{uuid.uuid4().hex[:10].upper()}"
        cur.execute(
            """INSERT INTO Payments
               (payment_id, booking_id, payment_amount, payment_method,
                payment_status, transaction_id, payment_gateway, created_at)
               VALUES (?, ?, ?, 'WhatsApp Pay', 'completed', ?, 'IndiGo Pay', ?)""",
            (payment_id, booking_id, total_amount, transaction_id, now),
        )

        conn.commit()
        return {"pnr_code": pnr_code, "transaction_id": transaction_id}

    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] save_booking: {e}")
        return {"pnr_code": "", "transaction_id": ""}
    finally:
        conn.close()
