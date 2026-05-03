import os
import sqlite3
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "indigo_airline.db")

CITY_TO_CODE: Dict[str, str] = {
    "agra": "AGR",
    "agartala": "IXA",
    "ahmedabad": "AMD",
    "aizawl": "AJL",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "bhopal": "BHO",
    "bhubaneswar": "BBI",
    "chandigarh": "IXC",
    "chennai": "MAA",
    "madras": "MAA",
    "coimbatore": "CJB",
    "delhi": "DEL",
    "new delhi": "DEL",
    "goa": "GOI",
    "panaji": "GOI",
    "guwahati": "GAU",
    "hyderabad": "HYD",
    "indore": "IDR",
    "jaipur": "JAI",
    "jammu": "IXJ",
    "kolkata": "CCU",
    "calcutta": "CCU",
    "kochi": "COK",
    "cochin": "COK",
    "kozhikode": "CCJ",
    "lucknow": "LKO",
    "leh": "IXL",
    "ludhiana": "LUH",
    "mangalore": "IXE",
    "mumbai": "BOM",
    "bombay": "BOM",
    "nagpur": "NAG",
    "patna": "PAT",
    "pune": "PNQ",
    "raipur": "RPR",
    "ranchi": "IXR",
    "srinagar": "SXR",
    "surat": "STV",
    "thiruvananthapuram": "TRV",
    "trivandrum": "TRV",
    "vadodara": "BDQ",
    "varanasi": "VNS",
    "visakhapatnam": "VTZ",
    "vizag": "VTZ",
}

CODE_TO_AIRPORT: Dict[str, str] = {
    "AGR": "Agra Airport",
    "AMD": "Sardar Vallabhbhai Patel International Airport",
    "BLR": "Kempegowda International Airport",
    "BOM": "Chhatrapati Shivaji Maharaj International Airport",
    "CCU": "Netaji Subhas Chandra Bose International Airport",
    "COK": "Cochin International Airport",
    "DEL": "Indira Gandhi International Airport",
    "GAU": "Lokpriya Gopinath Bordoloi International Airport",
    "GOI": "Goa International Airport",
    "HYD": "Rajiv Gandhi International Airport",
    "IDR": "Devi Ahilya Bai Holkar Airport",
    "IXC": "Chandigarh Airport",
    "JAI": "Jaipur International Airport",
    "LKO": "Chaudhary Charan Singh International Airport",
    "MAA": "Chennai International Airport",
    "NAG": "Dr. Babasaheb Ambedkar International Airport",
    "PAT": "Jay Prakash Narayan International Airport",
    "PNQ": "Pune Airport",
    "SXR": "Sheikh ul-Alam International Airport",
    "TRV": "Trivandrum International Airport",
    "VNS": "Lal Bahadur Shastri International Airport",
    "VTZ": "Visakhapatnam Airport",
}


def city_to_code(city: str) -> str:
    return CITY_TO_CODE.get(city.lower().strip(), city.upper()[:3])


def get_airport_name(code: str) -> str:
    return CODE_TO_AIRPORT.get(code.upper(), code)


def _minutes_to_duration(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h}h {m:02d}m"


def fetch_flights(departure_city: str, destination_city: str, travel_date: str) -> List[Dict]:
    origin_code = city_to_code(departure_city)
    dest_code = city_to_code(destination_city)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT fs.flight_id,
                   fs.origin_airport_code  AS origin,
                   fs.destination_airport_code AS destination,
                   fs.departure_time,
                   fs.arrival_time,
                   fs.flight_duration_minutes
            FROM FlightSchedule fs
            JOIN FlightInstances fi ON fs.flight_id = fi.flight_id
            WHERE fs.origin_airport_code = ?
              AND fs.destination_airport_code = ?
              AND fi.flight_date = ?
              AND (fs.status IS NULL OR fs.status = 'active')
            ORDER BY fs.departure_time
            LIMIT 12
            """,
            (origin_code, dest_code, travel_date),
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
