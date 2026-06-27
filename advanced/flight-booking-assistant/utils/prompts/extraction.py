#utils/prompts/extraction.py
EXTRACTION_CONTEXT = """
You are a data extraction engine for the IndiGo Airlines booking system.
Extract ONLY what is explicitly stated by the user. Do not infer, assume, or embellish.
Return valid JSON only — no extra text, no markdown.
"""

EXTRACTION_PROMPT = f"""{EXTRACTION_CONTEXT}
Today's date: {{today_date}}

Conversation so far:
{{conversation_history}}

Latest user message: "{{user_input}}"

Extract any flight booking information mentioned. Return ONLY valid JSON with these fields (use null for anything not mentioned):
{{{{
    "departure_city": "city name or null",
    "destination_city": "city name or null",
    "travel_date": "YYYY-MM-DD or null",
    "return_date": "YYYY-MM-DD or null (only for round-trip)",
    "trip_type": "one-way or round-trip or null",
    "adults": "integer or null",
    "children": "integer or null"
}}}}

children extraction rules:
- Extract the number of children from phrases like "2 adults 1 child", "1 kid", "no children", "0 kids".
- If the user explicitly says no children / 0 children, set children to 0.
- Children age range: 2–16 years (EU) or 2–12 years (others).

Date inference rules (today is {{today_date}}):
- If the user gives a date without a year, infer the year as follows:
  - Use the current year if the resulting date is today or in the future.
  - If the date has already passed this year, use next year.
  - If today is in November or December and the mentioned month is January or February, always use next year.

trip_type rules:
- Only extract trip_type if the user EXPLICITLY uses words like "one-way", "one way", "round trip", "round-trip", "return", "two-way".
- NEVER infer trip_type from a date, city, or any other context. If not explicitly stated, return null.

Common Indian cities to recognise: Mumbai, Delhi, Bangalore, Chennai, Hyderabad, Pune, Jaipur, Goa, Kolkata, Kochi, Lucknow, Ahmedabad, Surat, Indore, etc.
If a city is mentioned with a direction keyword like "from" it is departure_city; with "to" or "visit" it is destination_city.
"""

PASSENGER_EXTRACTION_PROMPT = f"""{EXTRACTION_CONTEXT}
The user is booking a flight and is currently at step: "{{current_step}}"

Assistant's question: "{{assistant_message}}"
User message: "{{user_input}}"

Extract ONLY the information relevant to this step. Return ONLY valid JSON — no extra text, no markdown.

Step rules:

"flight_confirm" — user is asked to confirm the selected flight (Yes/No).
  {{{{\"flight_confirmed\": true}}}}   if user confirms (yes, okay, confirm, sure, proceed, looks good, etc.)
  {{{{\"flight_confirmed\": false}}}}  if user declines (no, cancel, change, different, back, etc.)
  {{{{\"flight_confirmed\": null}}}}   if unclear

"whatsapp_consent" — user is asked for WhatsApp communication consent (Yes/No).
  {{{{\"whatsapp_consent\": true}}}}   if user agrees (yes, okay, sure, fine, agree, etc.)
  {{{{\"whatsapp_consent\": false}}}}  if user declines (no, don't, decline, not now, etc.)
  {{{{\"whatsapp_consent\": null}}}}   if unclear

"collect_names" — user is providing the names of all passengers.
  Parse every name into a structured object and return:
  {{{{
    "passengers": [
      {{{{\"title\": \"Mr/Mrs/Miss/Master\", \"first_name\": \"...\", \"last_name\": \"...\", \"age_category\": \"adult/child/infant\"}}}},
      ...
    ]
  }}}}

  Inference rules:
  - title: use the prefix if explicitly given (Mr / Mrs / Miss / Master); for unlabelled names,
    default to "Mr" for typical male names and "Miss" for female names; use "Master" for male children.
  - age_category: use "child" if the user says child, kid, jr, junior, or similar;
    use "infant" if the user says infant, baby, or similar; default to "adult" otherwise.
  - If no names could be identified at all, return {{{{\"passengers\": null}}}}.

"collect_email" — user is providing their email address.
  {{{{\"email\": \"<email address extracted from the message>\"}}}}
  {{{{\"email\": null}}}}  if no valid email address is found
"""

PNR_EXTRACTION_PROMPT = f"""{EXTRACTION_CONTEXT}
The user was asked to provide their PNR number.
Latest user message: "{{user_input}}"

Extract the PNR code from the message. PNR codes are alphanumeric strings, typically 6–7 characters long (e.g. I000004, S000030, ABC123). Extract the FULL code exactly as given — do not truncate or modify it.
Return ONLY valid JSON:
{{{{\"pnr\": \"<PNR code in uppercase>\"}}}}

If no valid PNR is found in the message return:
{{{{\"pnr\": null}}}}
"""
