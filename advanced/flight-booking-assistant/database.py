import sqlite3
from typing import List, Dict, Optional


class IndigoDB:
    def __init__(self, db_path: str = "advanced/flight-booking-assistant/indigo_airline.db"):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search_flights(self, origin_code: str, destination_code: str, travel_date: str) -> List[Dict]:
        """Search scheduled flight instances for a given date and route.

        Returns a list of dicts with flight and instance details.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT fs.flight_id,
                   fi.flight_instance_id,
                   fs.origin_airport_code AS origin,
                   fs.destination_airport_code AS destination,
                   fi.flight_date,
                   fi.scheduled_departure,
                   fi.scheduled_arrival,
                   fs.departure_time AS route_departure_time,
                   fs.arrival_time AS route_arrival_time,
                   fs.flight_duration_minutes,
                   fs.aircraft_type,
                   fs.seat_capacity,
                   fi.flight_status
            FROM FlightSchedule fs
            JOIN FlightInstances fi ON fs.flight_id = fi.flight_id
            WHERE fs.origin_airport_code = ?
              AND fs.destination_airport_code = ?
              AND fi.flight_date = ?
            ORDER BY fi.scheduled_departure
            """,
            (origin_code, destination_code, travel_date),
        )

        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_booking(self, booking_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Bookings WHERE booking_id = ?", (booking_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        booking = dict(row)

        # attach itinerary info
        cur.execute("SELECT * FROM Itineraries WHERE booking_id = ?", (booking_id,))
        itin = cur.fetchone()
        booking["itinerary"] = dict(itin) if itin else None

        conn.close()
        return booking

    def get_customer(self, customer_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Customers WHERE customer_id = ?", (customer_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_passengers_by_booking(self, booking_id: str) -> List[Dict]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM Passengers WHERE booking_id = ?", (booking_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_itinerary_legs(self, itinerary_id: str) -> List[Dict]:
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ItineraryLegs WHERE itinerary_id = ? ORDER BY leg_number", (itinerary_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_airport_name(self, code: str) -> str:
        airports = {
            "BOM": "Chhatrapati Shivaji International Airport",
            "JAI": "Jaipur International Airport",
            "DEL": "Indira Gandhi International Airport",
            "BLR": "Kempegowda International Airport",
            "HYD": "Rajiv Gandhi International Airport",
            "MAA": "Chennai International Airport",
            "PNQ": "Pune Airport",
            "CCU": "Netaji Subhas Chandra Bose International Airport",
            "GOI": "Goa International Airport",
        }
        return airports.get(code, code)