from typing import Dict

SESSION_TTL_SECONDS = 1800
MAX_SLOT_ATTEMPTS = 3

TERMINATION_MESSAGE = (
    "Sorry about that, but I'm having a bit of trouble understanding your messages "
    "as I'm still learning to improve.\n\n"
    "Please try fresh or connect with our customer care executive at 0124-12345678\n\n"
    "Thank you for your patience."
)

INITIAL_GREETING = (
    "Hello! Welcome to IndiGo Airlines. I'm 6ESkai, your virtual booking assistant.\n\n"
    "I can help you with:\n"
    "• Flight booking\n"
    "• Web check-in\n"
    "• Flight status\n\n"
    "How can I assist you today?"
)

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
