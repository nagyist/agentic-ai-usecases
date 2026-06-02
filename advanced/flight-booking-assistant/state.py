from typing import TypedDict, List, Dict


class Passenger(TypedDict):
    title: str          # "Mr" | "Mrs" | "Miss" | "Master"
    first_name: str
    last_name: str
    age_category: str   # "adult" | "child" | "infant"


class SessionState(TypedDict):
    """Channel and session lifecycle. Owned by: app.py, telegram_bot.py."""
    session_id: str                  # UUID generated on session start
    user_id: str                     # WhatsApp phone number or Telegram chat_id
    channel: str                     # "web" | "telegram" | "whatsapp"
    started_at: str                  # ISO datetime of session creation
    last_active_at: str              # ISO datetime, updated on every turn


class ConversationState(TypedDict):
    """Dialog flow and turn-level I/O. Owned by: router.py, conversation_driver.py, graph.py."""
    messages: List[Dict[str, str]]   # full chat history [{"role": ..., "content": ...}]
    last_user_input: str
    assistant_message: str
    step: str                        # GREETING | COLLECT_SLOTS | CONFIRM_BOOKING | SHOW_FLIGHTS
                                     # | flight_confirm | whatsapp_consent | collect_names
                                     # | collect_email | PAYMENT
    current_agent: str               # shown in sidebar
    process: str                     # "book_flight" | "web_checkin" | "flight_status" | ""
    intent: str
    flow_history: List[str]          # ordered log of steps visited this session
    terminated: bool                 # True when a slot exceeds 3 failed attempts → end session
    awaiting_confirmation: bool      # True while user is reviewing the pre-search summary


class BookingEntities(TypedDict):
    """Domain data collected from the user. Owned by: information_extractor.py, slot_validator.py, city_lookup.py."""
    pnr: str                         # PNR code for web check-in / flight status
    departure_city: str              # user-facing city name, e.g. "Mumbai"
    destination_city: str            # user-facing city name, e.g. "Delhi"
    departure_airport_code: str      # IATA code resolved by city_lookup, e.g. "BOM"
    destination_airport_code: str    # IATA code resolved by city_lookup, e.g. "DEL"
    travel_date: str                 # YYYY-MM-DD
    return_date: str                 # YYYY-MM-DD, only for round-trip
    trip_type: str                   # "one-way" or "round-trip"
    adults: int
    children: int
    flight_confirmed: bool           # extracted yes/no from flight_confirm step
    whatsapp_consent: bool
    passengers: List[Passenger]      # structured passenger list, one entry per traveller
    email: str


class FlightState(TypedDict):
    """Search results and post-selection flow. Owned by: graph.py (search_flights_node), flight_selection.py, payment.py."""
    flights: List[Dict]
    selected_flight: Dict
    booking_leg: str                 # "outbound" | "return"
    selected_outbound_flight: Dict   # stored after user confirms outbound leg
    selected_return_flight: Dict     # stored after user confirms return leg
    confirmation_step: str           # flight_confirm | whatsapp_consent | collect_names | collect_email
    passenger_error: str             # validation error message, consumed by passenger_driver


class ValidationState(TypedDict):
    """Error flags and retry tracking. Owned by: city_lookup.py, slot_validator.py, conversation_driver.py."""
    cities_changed: List[str]        # which city fields are new/changed this turn; drives city_lookup
    cities_updated: bool             # True when cities_changed is non-empty (used by graph routing)
    slots_updated: bool              # True when any flight slot changed this turn
    city_error: str                  # set by city_lookup when a city has no airport; cleared after use
    slot_error: str                  # set by validate_slots when a date/passenger field is invalid; cleared after use
    slot_attempts: Dict[str, int]    # retry count per slot field, e.g. {"travel_date": 2}
    name_attempts: int               # retry count for passenger name collection


class BookingState(
    SessionState,
    ConversationState,
    BookingEntities,
    FlightState,
    ValidationState,
):
    """
    Single LangGraph state shared across all nodes.
    Fields are flat at runtime — sub-types document ownership only.
    """
    pass


# Canonical default — import this in every channel adapter instead of redefining it.
# Channel adapters may override "channel", "user_id", and "session_id" after copying.
INITIAL_STATE: Dict = {
    # SessionState
    "session_id": "",
    "user_id": "",
    "channel": "web",
    "started_at": "",
    "last_active_at": "",
    # ConversationState
    "messages": [],
    "last_user_input": "",
    "assistant_message": "",
    "step": "GREETING",
    "current_agent": "router",
    "process": "",
    "intent": None,
    "flow_history": [],
    "terminated": False,
    "awaiting_confirmation": False,
    # BookingEntities
    "pnr": "",
    "departure_city": None,
    "destination_city": None,
    "departure_airport_code": "",
    "destination_airport_code": "",
    "travel_date": None,
    "return_date": None,
    "trip_type": None,
    "adults": None,
    "children": None,
    "flight_confirmed": None,
    "whatsapp_consent": None,
    "passengers": [],
    "email": "",
    # FlightState
    "flights": [],
    "selected_flight": {},
    "booking_leg": "",
    "selected_outbound_flight": {},
    "selected_return_flight": {},
    "confirmation_step": "",
    "passenger_error": "",
    # ValidationState
    "cities_changed": [],
    "cities_updated": False,
    "slots_updated": False,
    "city_error": "",
    "slot_error": "",
    "slot_attempts": {},
    "name_attempts": 0,
}
