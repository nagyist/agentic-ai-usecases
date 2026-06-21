from typing import Dict


class Step:
    GREETING = "GREETING"
    SHOW_MENU = "SHOW_MENU"
    COLLECT_SLOTS = "COLLECT_SLOTS"
    CONFIRM_BOOKING = "CONFIRM_BOOKING"
    SHOW_FLIGHTS = "SHOW_FLIGHTS"
    COLLECT_PNR = "COLLECT_PNR"
    SEARCH_FLIGHTS = "SEARCH_FLIGHTS"
    SEARCH_RETURN_FLIGHTS = "SEARCH_RETURN_FLIGHTS"
    PAYMENT = "PAYMENT"
    DONE = "DONE"
    EXTRACTED = "EXTRACTED"
    CITY_VALIDATED = "CITY_VALIDATED"
    FLIGHT_CONFIRM = "flight_confirm"
    WHATSAPP_CONSENT = "whatsapp_consent"
    COLLECT_NAMES = "collect_names"
    COLLECT_EMAIL = "collect_email"


class Intent:
    BOOK_FLIGHT = "book_flight"
    WEB_CHECKIN = "web_checkin"
    FLIGHT_STATUS = "flight_status"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"


class Process:
    BOOK_FLIGHT = "book_flight"
    WEB_CHECKIN = "web_checkin"
    FLIGHT_STATUS = "flight_status"


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
