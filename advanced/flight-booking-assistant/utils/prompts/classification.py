CONFIRM_INTENT_PROMPT = """
The user has been shown their travel summary and asked to confirm or make changes.

User message: "{user_input}"

Classify the user's intent into exactly one of three options and return ONLY valid JSON:

{{"intent": "affirm"}}   — user wants to proceed (e.g. yes, ok, sure, proceed, go ahead, don't stop, sounds good)
{{"intent": "deny"}}     — user wants to cancel or start over (e.g. no, cancel, don't proceed, start over)
{{"intent": "modify"}}   — user wants to change something (e.g. change destination, update date, different city)
"""

FLIGHT_SELECTION_PROMPT = """
Available flights (sequence number shown as Flight N, index is N-1):
{flights}

User said: "{user_input}"

Identify which flight the user wants. They may say "flight 1", "flight 5", "the cheapest", a flight number like "6E0863", or a departure time.
When the user says "flight N", the selected_index is N-1 (e.g. "flight 5" → selected_index 4).
Return ONLY valid JSON:
{{"selected_index": <0-based integer index into the flights list>}}

If you cannot determine a valid selection return:
{{"selected_index": null}}
"""

MID_FLOW_INTENT_PROMPT = """
The user is in the middle of a flight booking. They have already seen available flights.

Current step: {step}
User said: "{user_input}"

Classify the user's intent:
- "modify"   : user wants to change any booking detail (destination, departure city, date, passengers)
               Examples: "change destination to goa", "different date", "I want to go to Delhi instead", "update departure"
- "continue" : user is selecting a flight or answering the current question
               Examples: "flight 1", "the cheapest", "yes", "no", "9:00 AM"

Return ONLY valid JSON — no extra text:
{{"intent": "modify"}}
{{"intent": "continue"}}
"""

CITY_LOOKUP_PROMPT = """
A user mentioned the city "{input_city}" while booking a flight.

Here are the airport cities we serve that most closely match that input:
{candidates}

Your task:
- If one of the candidates clearly matches what the user intended (same city, common alias, or obvious typo), return that candidate's exact name.
- If the list is empty or none of the candidates is a plausible match, return null.

Return ONLY valid JSON — no extra text:
{{"resolved_city": "<exact candidate name or null>"}}
"""
