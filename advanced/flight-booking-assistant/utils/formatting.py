from datetime import datetime


def format_date(date_str: str, fmt: str = "%d %B %Y") -> str:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime(fmt)
    except Exception:
        return date_str


def format_flight_block(label: str, flight: dict, date_str: str, adults: int) -> str:
    price = flight.get("price", 0)
    return (
        f"{label}\n"
        f"Date        : {date_str}\n"
        f"Flight      : {flight.get('flight_number', '')}\n"
        f"Departure   : {flight.get('departure_time', '')}\n"
        f"Arrival     : {flight.get('arrival_time', '')}\n"
        f"Duration    : {flight.get('duration', '')}\n"
        f"Non-stop\n"
        f"Adult(s)    {adults} x Rs.{price}    Rs.{price * adults}\n"
    )


def format_passengers(passengers: list) -> str:
    if not passengers:
        return ""
    lines = []
    for p in passengers:
        title = p.get("title", "")
        first = p.get("first_name", "")
        last = p.get("last_name", "")
        category = p.get("age_category", "adult")
        lines.append(f"{title} {first} {last} ({category})".strip())
    return "\n".join(lines)
