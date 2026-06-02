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
