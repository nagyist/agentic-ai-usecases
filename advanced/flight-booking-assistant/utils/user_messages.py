"""
User-facing fixed strings for the conversation driver.
These are sent directly to the user — they are NOT fed to an LLM.
"""

SLOT_QUESTIONS = {
    "destination_city": "Please let us know your destination city.",
    "departure_city":   "Which city will you be flying from?",
    "trip_type":        "Will this be a one-way or round-trip journey?",
    "passengers": (
        "Can you please tell me the number of passengers?\n"
        "eg. 2 adults, 1 child\n\n"
        "Child age range:\n"
        "EU region - between 2 and 16 years\n"
        "Others    - between 2 and 12 years\n\n"
        "If no children, please say 0 children."
    ),
}

SLOT_LABELS = {
    "destination_city": "destination city",
    "departure_city":   "departure city",
    "travel_date":      "travel date",
    "return_date":      "return date",
    "trip_type":        "trip type (one-way or round-trip)",
    "passengers":       "number of passengers",
}

TRAVEL_DATE_QUESTION = "Which date would you like to travel? (e.g. {example})"
RETURN_DATE_QUESTION  = "What is your return date? (e.g. {example})"

PNR_PROMPTS = {
    "web_checkin":   "To initiate web check-in process, please provide your PNR number.",
    "flight_status": "To check your flight status and terminal, please provide your PNR number.",
}

WHATSAPP_CONSENT_MESSAGE = (
    "To keep you informed about our products and services, we would like your consent "
    "to communicate with you on WhatsApp. By confirming Yes, you agree to IndiGo's "
    "Privacy Policy and Consent Management Policy.\n"
    "https://www.goindigo.in/information/privacy.html\n\n"
    "Option - Yes\n"
    "Option - No"
)

PASSENGER_NAME_MESSAGE = (
    "Okay, continuing with the process.\n\n"
    "Can you please tell me the full name of all the passengers?\n"
    "eg: Mr./Mrs./Miss First Name Last Name\n\n"
    "Please provide all names together in one message."
)

EMAIL_MESSAGE = (
    "Please provide your email address in the correct format.\n"
    "eg: email_id@website.com"
)

FLIGHT_CONFIRM_REASK = (
    "Please reply Yes to confirm the flight or No to pick a different one.\n"
    "Option - Yes\n"
    "Option - No"
)
