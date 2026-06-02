import os
import sqlite3
from typing import List, Dict
from config import CITY_TO_CODE, CODE_TO_AIRPORT

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "indigo_airline.db")


def city_to_code(city: str) -> str:
    return CITY_TO_CODE.get(city.lower().strip(), city.upper()[:3])


def get_candidate_cities(query: str, top_n: int = 10) -> list:
    """Return up to top_n city name candidates using substring + fuzzy matching."""
    import difflib
    query_lower = query.lower().strip()
    city_names = list(CITY_TO_CODE.keys())

    # Substring matches (query contained in city name or vice-versa)
    substring = [c for c in city_names if query_lower in c or c in query_lower]

    # Fuzzy close matches
    fuzzy = difflib.get_close_matches(query_lower, city_names, n=top_n, cutoff=0.4)

    # Combine, preserve order, deduplicate
    seen = set()
    combined = []
    for c in substring + fuzzy:
        if c not in seen:
            seen.add(c)
            combined.append(c)

    return combined[:top_n]


def get_airport_name(code: str) -> str:
    return CODE_TO_AIRPORT.get(code.upper(), code)


def _minutes_to_duration(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m:02d}m"


def fetch_pnr_info(pnr_code: str) -> Dict:
    """Return combined PNR + booking + flight info, or an empty dict if not found."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                p.pnr_code,
                p.pnr_status,
                b.booking_id,
                b.flight_id,
                b.flight_date,
                b.booking_status,
                b.total_passengers,
                b.final_amount,
                fs.origin_airport_code      AS origin,
                fs.destination_airport_code AS destination,
                fs.departure_time,
                fs.arrival_time,
                fs.flight_duration_minutes,
                fi.flight_status            AS live_status,
                fi.actual_departure,
                fi.actual_arrival,
                fi.scheduled_departure,
                fi.scheduled_arrival
            FROM PNRs p
            JOIN Bookings b          ON p.pnr_code   = b.pnr_code
            JOIN FlightSchedule fs   ON b.flight_id  = fs.flight_id
            LEFT JOIN FlightInstances fi
                ON fi.flight_id   = b.flight_id
               AND fi.flight_date = b.flight_date
            WHERE p.pnr_code = ?
            LIMIT 1
            """,
            (pnr_code.upper().strip(),),
        )
        row = cur.fetchone()

        if not row:
            conn.close()
            return {}

        row = dict(row)

        # Fetch passenger names
        cur.execute(
            """
            SELECT first_name, last_name, passenger_type
            FROM Passengers
            WHERE booking_id = ?
            """,
            (row["booking_id"],),
        )
        passengers = [dict(r) for r in cur.fetchall()]
        conn.close()

        duration_mins = row.get("flight_duration_minutes") or 0
        return {
            "pnr_code":        row["pnr_code"],
            "pnr_status":      row["pnr_status"],
            "booking_status":  row["booking_status"],
            "flight_id":       row["flight_id"],
            "flight_date":     row["flight_date"],
            "origin":          row["origin"],
            "destination":     row["destination"],
            "origin_airport":  get_airport_name(row["origin"]),
            "destination_airport": get_airport_name(row["destination"]),
            "departure_time":  str(row["departure_time"])[:5] if row["departure_time"] else "",
            "arrival_time":    str(row["arrival_time"])[:5] if row["arrival_time"] else "",
            "duration":        _minutes_to_duration(duration_mins),
            "live_status":     row.get("live_status") or "Scheduled",
            "actual_departure": row.get("actual_departure") or "",
            "actual_arrival":   row.get("actual_arrival") or "",
            "total_passengers": row["total_passengers"],
            "final_amount":     row["final_amount"],
            "passengers":       passengers,
        }

    except Exception as e:
        print(f"[DB ERROR] fetch_pnr_info: {e}")
        return {}


def fetch_flights(departure_city: str, destination_city: str) -> List[Dict]:
    origin_code = city_to_code(departure_city)
    dest_code = city_to_code(destination_city)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT flight_id,
                   origin_airport_code      AS origin,
                   destination_airport_code AS destination,
                   departure_time,
                   arrival_time,
                   flight_duration_minutes
            FROM FlightSchedule
            WHERE origin_airport_code      = ?
              AND destination_airport_code = ?
              AND (status IS NULL OR status = 'active')
            ORDER BY departure_time
            LIMIT 12
            """,
            (origin_code, dest_code),
        )
        rows = cur.fetchall()
        conn.close()

        flights = []
        for i, row in enumerate(rows):
            row = dict(row)
            duration_mins = row.get("flight_duration_minutes") or 120
            # price is not in the DB schema; use a reasonable base + index spread
            price = 2500 + (i % 4) * 400 + (duration_mins // 10) * 50
            flights.append({
                "flight_number": row["flight_id"],
                "departure_time": str(row["departure_time"])[:5],
                "arrival_time": str(row["arrival_time"])[:5],
                "duration": _minutes_to_duration(duration_mins),
                "price": price,
                "origin": row["origin"],
                "destination": row["destination"],
            })
        return flights

    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []
