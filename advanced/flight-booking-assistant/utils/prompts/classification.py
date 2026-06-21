CONFIRM_INTENT_PROMPT = """
The user has been shown their travel summary and asked to confirm or make changes.

User message: "{user_input}"

Classify the user's intent into exactly one of three options and return ONLY valid JSON:

{{"intent": "affirm"}}   — user wants to proceed (e.g. yes, ok, sure, proceed, go ahead, don't stop, sounds good)
{{"intent": "deny"}}     — user wants to cancel or start over (e.g. no, cancel, don't proceed, start over)
{{"intent": "modify"}}   — user wants to change something (e.g. change destination, update date, different city)
"""

FLIGHT_SELECTION_PROMPT = """
Available flights:
{flights}

User said: "{user_input}"

Identify which flight the user wants. They may say "flight 1", "the cheapest", a flight number, or a departure time.
Return ONLY valid JSON:
{{"selected_index": <0-based integer index into the flights list>}}

If you cannot determine a valid selection return:
{{"selected_index": null}}
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
