from typing import TypedDict, List, Dict


class BookingState(TypedDict):
    # Conversation
    messages: List[Dict[str, str]]   # full chat history [{"role": ..., "content": ...}]
    last_user_input: str
    assistant_message: str
    step: str                        # GREETING | COLLECT_SLOTS | CONFIRM_BOOKING | SHOW_FLIGHTS
                                     # | flight_confirm | whatsapp_consent | collect_names
                                     # | collect_email | PAYMENT
    current_agent: str               # shown in sidebar

    # Booking info (flat fields)
    intent: str
    departure_city: str              # user-facing city name, e.g. "Mumbai"
    destination_city: str            # user-facing city name, e.g. "Delhi"
    travel_date: str                 # YYYY-MM-DD
    trip_type: str                   # "one-way" or "round-trip"
    adults: int
    children: int

    # Post-selection confirmation sub-steps
    confirmation_step: str           # flight_confirm | whatsapp_consent | collect_names | collect_email
    whatsapp_consent: bool
    passenger_names: str
    email: str

    # Flights
    flights: List[Dict]
    selected_flight: Dict
