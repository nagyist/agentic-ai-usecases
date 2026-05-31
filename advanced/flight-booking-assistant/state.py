from typing import TypedDict, List, Dict


class Passenger(TypedDict):
    title: str          # "Mr" | "Mrs" | "Miss" | "Master"
    first_name: str
    last_name: str
    age_category: str   # "adult" | "child" | "infant"


class BookingState(TypedDict):
    # Session identity (required for WhatsApp / Telegram stateless channels)
    session_id: str                  # UUID generated on session start
    user_id: str                     # WhatsApp phone number or Telegram chat_id
    channel: str                     # "web" | "telegram" | "whatsapp"
    started_at: str                  # ISO datetime of session creation
    last_active_at: str              # ISO datetime, updated on every turn

    # Conversation
    messages: List[Dict[str, str]]   # full chat history [{"role": ..., "content": ...}]
    last_user_input: str
    assistant_message: str
    step: str                        # GREETING | COLLECT_SLOTS | CONFIRM_BOOKING | SHOW_FLIGHTS
                                     # | flight_confirm | whatsapp_consent | collect_names
                                     # | collect_email | PAYMENT
    current_agent: str               # shown in sidebar

    # Active process: "book_flight" | "web_checkin" | "flight_status" | ""
    process: str

    # Booking info (flat fields)
    intent: str
    pnr: str                          # PNR code for web check-in / flight status
    departure_city: str              # user-facing city name, e.g. "Mumbai"
    destination_city: str            # user-facing city name, e.g. "Delhi"
    departure_airport_code: str      # IATA code resolved by city_lookup, e.g. "BOM"
    destination_airport_code: str    # IATA code resolved by city_lookup, e.g. "DEL"
    travel_date: str                 # YYYY-MM-DD
    return_date: str                 # YYYY-MM-DD, only for round-trip
    trip_type: str                   # "one-way" or "round-trip"
    adults: int
    children: int

    # Post-selection confirmation sub-steps
    confirmation_step: str           # flight_confirm | whatsapp_consent | collect_names | collect_email
    flight_confirmed: bool           # extracted yes/no from flight_confirm step
    whatsapp_consent: bool
    passengers: List[Passenger]      # structured passenger list, one entry per traveller
    passenger_error: str             # validation error message, consumed by passenger_driver
    email: str

    # City validation
    cities_changed: List[str]        # which city fields are new/changed this turn; drives city_lookup
    cities_updated: bool             # True when cities_changed is non-empty (used by graph routing)
    slots_updated: bool              # True when any flight slot changed this turn
    city_error: str                  # set by city_lookup when a city has no airport; cleared after use
    slot_error: str                  # set by validate_slots when a date/passenger field is invalid; cleared after use

    # Confirmation context
    awaiting_confirmation: bool      # True while user is reviewing the pre-search summary

    # Flights
    flights: List[Dict]
    selected_flight: Dict
    booking_leg: str                  # "outbound" | "return"
    selected_outbound_flight: Dict    # stored after user confirms outbound leg
    selected_return_flight: Dict      # stored after user confirms return leg

    # Operational / analytics
    flow_history: List[str]          # ordered log of steps visited this session
    slot_attempts: Dict[str, int]    # retry count per slot field, e.g. {"travel_date": 2}
    name_attempts: int               # retry count for passenger name collection
    terminated: bool                 # True when a slot exceeds 3 failed attempts → end session
