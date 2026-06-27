# IndiGo Flight Booking Assistant — 6ESkai

A production-grade conversational AI agent for IndiGo Airlines, built with **LangGraph** and **OpenAI GPT-4o-mini**. Supports flight booking (one-way and round-trip), web check-in, and flight status enquiries across a Streamlit web UI and a Telegram bot — both backed by the same compiled state machine.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Supported Processes](#supported-processes)
- [Conversation Flow](#conversation-flow)
- [Key Design Decisions](#key-design-decisions)
- [Available Routes](#available-routes)
- [Technology Stack](#technology-stack)
- [How to Extend](#how-to-extend)

---

## Quick Start

**Prerequisites:** Python 3.11+, an OpenAI API key.

```bash
git clone https://github.com/vijendrajain/agentic-ai-usecases
cd advanced/flight-booking-assistant
pip install -r requirements.txt
```

Create a `.env` file:

```
OPENAI_API_KEY=sk-...
```

Run the Streamlit web app:

```bash
streamlit run app.py
```

Open `http://localhost:8501`. The assistant greets you and is ready.

To run the Telegram bot, add your bot token to `.env`:

```
TELEGRAM_BOT_TOKEN=<your-bot-token>
```

Then:

```bash
python telegram_bot.py
```

---

## Project Structure

```
flight-booking-assistant/
├── app.py                       ← Streamlit web UI (primary entry point)
├── telegram_bot.py              ← Telegram bot adapter
├── state.py                     ← BookingState TypedDict (5 sub-types + Passenger)
├── constants.py                 ← Step, Intent, Process enums
├── config.py                    ← Settings loaded from .env
├── create_airline_db.py         ← Script used to seed the database
│
├── graph/
│   ├── __init__.py              ← Top-level StateGraph + dispatch_route
│   ├── booking_subgraph.py      ← Compiled booking flow (10 nodes)
│   └── pnr_subgraph.py          ← Compiled PNR / check-in / status flow (3 nodes)
│
├── nodes/                       ← All node functions (LLM-calling and pure-Python)
│   ├── router.py                ← Intent classification (booking / check-in / status)
│   ├── information_extractor.py ← Slot, PNR, and passenger extraction
│   ├── slot_validator.py        ← Per-field validation + retry counter updates
│   ├── city_lookup.py           ← City name → IATA code resolution
│   ├── conversation_driver.py   ← Slot sequencing, Phase 1 & 2 flow orchestration
│   ├── flight_selection.py      ← Parses user's flight choice from numbered list
│   ├── booking_guardrail.py     ← Guards against mid-flow process switching
│   ├── confirmation.py          ← Pre-search booking confirmation prompt
│   ├── payment.py               ← Payment summary (stub, ready for Stripe/Razorpay)
│   └── done.py                  ← Writes booking to DB, generates PNR, teardown
│
├── services/
│   ├── flight_search.py         ← SQLite flight query + dynamic pricing
│   ├── pnr_lookup.py            ← PNR / check-in / flight status lookup
│   ├── booking_save.py          ← Persists confirmed bookings, generates PNR
│   └── session_store.py         ← Session persistence across page refreshes
│
├── utils/
│   ├── llm.py                   ← call_llm_json wrapper + observability logging
│   ├── db.py                    ← SQLite connection and query helpers
│   ├── formatting.py            ← Flight list and message formatters
│   ├── user_messages.py         ← User-facing string constants
│   └── prompts/
│       ├── extraction.py        ← Slot, PNR, passenger extraction prompts
│       ├── conversation.py      ← Routing, retry, persona prompts
│       └── classification.py   ← Intent classification prompts
│
├── indigo_airline.db            ← Pre-loaded SQLite database (17 tables)
├── sessions.db                  ← Session state persistence across page refreshes
└── requirements.txt
```

---

## Architecture

### Top-Level Graph

Every user message enters through a single compiled graph. A pure-Python dispatcher reads `state["step"]` and routes without any LLM call — the LLM only fires on the very first message of a new session.

```
Every user message
        │
        ▼
  dispatch_route()    ← pure Python, reads state["step"], no LLM
        │
   ┌────┼─────────────────────────────────────────────┐
   │    │                                             │
   ▼    ▼                                             ▼
 step   step in _BOOKING_STEPS               step in _PNR_STEPS
 is     (mid-booking)                        (mid-PNR lookup)
 GREET  │                                    │
   │    └──────────────────┐                 └──────────────┐
   ▼                       ▼                               ▼
"router"               "booking"                        "pnr"
(LLM runs,             (skip router entirely)           (skip router entirely)
 classifies intent)
   │
   ▼
route_after_router()   ← pure Python, reads state["intent"]
   │
   ├─ book_flight    → booking_subgraph
   ├─ web_checkin    → pnr_subgraph
   ├─ flight_status  → pnr_subgraph
   └─ greeting/out   → END
```

### Booking Subgraph (10 nodes)

```
Incoming turn
      │
      ▼
booking_guardrail  ← intercepts mid-flow changes (e.g. "change destination to Goa")
      │
  _dispatch()      ← lookup table: step → node
      │
      ├─ COLLECT_SLOTS / new → info_extractor
      ├─ SHOW_FLIGHTS         → select  → END
      ├─ CONFIRM_BOOKING      → confirm
      ├─ PAYMENT              → payment → END
      ├─ DONE                 → done    → END
      └─ FLIGHT_CONFIRM /
         WHATSAPP_CONSENT /
         COLLECT_NAMES /
         COLLECT_EMAIL        → info_extractor
                                    │
                          _after_info_extractor()
                                    │
                          ┌─────────┴─────────────────┐
                          │                           │
                     step == EXTRACTED           everything else
                          │                           │
                          ▼                           ▼
                   validate_slots             conversation_driver → END
                          │
               _after_validate_slots()
                          │
                  ┌───────┴──────────┐
                  │                  │
             slot_error?        cities changed?
                  │                  │
                  ▼                  ▼
         conversation_driver    city_lookup → conversation_driver → END
```

### PNR Subgraph (3 nodes)

Used for both **web check-in** and **flight status** queries. The conversation driver asks for the PNR and returns END; extraction happens on the next turn.

```
Incoming turn
      │
      ▼
  _dispatch()
      │
   ┌──┴──────────────────────────────────┐
   │                                     │
   ▼                                     ▼
conversation_driver                info_extractor
(asks for PNR → END)                    │
                             _after_info_extractor()
                                         │
                             ┌───────────┴───────────────┐
                             │                           │
                             ▼                           ▼
                    conversation_driver → END      pnr_lookup → END
                    (re-ask if PNR not found)
```

### LLM Call Points

| Node | Prompt family | Purpose |
|------|--------------|---------|
| `router` | Conversation | Classify intent from first message |
| `info_extractor` | Extraction | Extract slots / passenger names / PNR |
| `city_lookup` | Classification | Resolve city name to IATA code |
| `booking_guardrail` | Classification | Detect mid-flow modification intent |
| `confirmation` | Classification | Parse yes / no / modify from confirmation reply |
| `flight_selection` | Classification | Map natural language to a flight index |
| `conversation_driver` | Conversation | Generate slot questions and retry messages |

All LLM calls use `response_format={"type": "json_object"}` and `temperature=0`, enforced in `utils/llm.py`. Every call is logged with prompt, output, token counts, and latency.

---

## Supported Processes

| Process | Trigger phrases | Description |
|---------|----------------|-------------|
| `book_flight` | "Book a ticket", "I want to fly to Delhi" | Multi-turn booking (one-way or round-trip) |
| `web_checkin` | "Web check-in", "Check in for my flight" | PNR lookup → check-in eligibility display |
| `flight_status` | "Flight status", "Where is my flight" | PNR lookup → live flight status display |

Switching processes mid-session is blocked by `booking_guardrail`. Type **"exit"** to reset.

---

## Conversation Flow

### Book Flight (typical)

```
User: "Book a flight to Mumbai"
  └─ Router → book_flight
       └─ Info Extractor → destination = Mumbai extracted
            └─ Conversation Driver → asks for origin city

User: "From Jaipur"
  └─ Info Extractor → departure = Jaipur
       └─ Conversation Driver → asks for travel date

User: "15th July, one-way, 2 adults"
  └─ Info Extractor → date, trip_type, adults all extracted
       └─ Slot Validator → date valid
            └─ City Lookup → JAI, BOM resolved
                 └─ Conversation Driver → shows travel summary, asks to confirm

User: "Yes"
  └─ Confirmation → affirm
       └─ Flight Search → shows available flights

User: "Flight 1"
  └─ Flight Selection → selects 6E101
       └─ Conversation Driver → confirms flight, collects WhatsApp consent,
                                 passenger names, email
            └─ Payment → displays booking summary

User: "Confirm"
  └─ Done → saves booking, generates PNR, displays confirmation
```

For **round-trip**, the flight search and selection step repeats for the return leg. `booking_leg` in state controls which leg is active.

### Web Check-in / Flight Status

```
User: "Web check-in"
  └─ Router → web_checkin → pnr_subgraph
       └─ Conversation Driver → asks for PNR → END

User: "I000042"
  └─ Info Extractor → pnr = I000042
       └─ PNR Lookup → fetches booking, formats check-in details → END
```

---

## Key Design Decisions

### State-Driven Routing

`state["step"]` is the single source of truth for where you are in the conversation. Every routing decision reads `step` first — no LLM call, no ambiguity. Mid-session resumption is a dictionary lookup, not a replay.

### Per-Field Retry Tracking

`slot_attempts: Dict[str, int]` tracks failure counts per field. A user who keeps entering past dates fails only the `travel_date` field — the session stays alive. A global counter would kill the session after three bad dates even if all other fields were correct. Maximum 3 attempts per field; after that `terminated = True`.

### Incremental Passenger Name Collection

Passengers can send names across multiple turns. The extractor accumulates them: `combined = existing + [p for p in val if p not in existing]`. The conversation driver shows what has been recorded and asks for the remaining names. Partial input is not counted as a failure.

### PNR Code Extraction

PNR codes in this database are alphanumeric strings, typically 6–7 characters (e.g. `I000004`, `S000030`). The extraction prompt instructs the model to return the **full code exactly as given** — no truncation, uppercase only.

### Prompt Separation

Eleven prompts are split into three families:
- **Extraction** (`utils/prompts/extraction.py`) — strict JSON, null for anything not stated, no inference
- **Classification** (`utils/prompts/classification.py`) — closed vocabulary, one bucket, no elaboration
- **Conversation** (`utils/prompts/conversation.py`) — free text, always bounded by `SYSTEM_PERSONA`

### Real Database, Not Mocks

Every query hits a real SQLite database. Pricing is computed dynamically (`2500 + (index % 4) * 400 + (duration_mins // 10) * 50`) — no fare table needed. The `done` node calls `services/booking_save.py` to persist the booking and generate a real PNR, which the user can immediately use for web check-in or status queries.

### Thin Channel Adapters

`app.py` (Streamlit) and `telegram_bot.py` contain no business logic — they call `booking_graph.invoke()` and display `result["assistant_message"]`. Adding a new channel means writing one adapter file.

---

## Available Routes

The database contains 12 IndiGo routes. Supported cities (resolved via fuzzy match + LLM):

| City | Code | Airport |
|------|------|---------|
| Delhi / New Delhi | DEL | Indira Gandhi International |
| Mumbai / Bombay | BOM | Chhatrapati Shivaji Maharaj International |
| Bangalore / Bengaluru | BLR | Kempegowda International |
| Jaipur | JAI | Jaipur International |
| Hyderabad | HYD | Rajiv Gandhi International |
| Kolkata / Calcutta | CCU | Netaji Subhas Chandra Bose International |
| Chennai / Madras | MAA | Chennai International |
| Kochi / Cochin | COK | Cochin International |
| Pune | PNQ | Pune Airport |
| Goa / Panaji | GOI | Goa International |
| Lucknow | LKO | Chaudhary Charan Singh International |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI GPT-4o-mini |
| Agent framework | LangGraph >= 1.0.7 |
| Web UI | Streamlit >= 1.50.0 |
| Bot channel | python-telegram-bot >= 21.0 |
| Database | SQLite3 (17 tables) |
| Config | python-dotenv |
| Language | Python 3.11+ |

---

## How to Extend

### Add a New Airport / City

Add entries to `constants.py` (`CITY_TO_CODE`) and `utils/db.py` (`CODE_TO_AIRPORT`).

### Add a New Intent / Process

1. Add the intent string to `constants.py` (`Intent` class)
2. Add routing logic to the `ROUTING_PROMPT` in `utils/prompts/conversation.py`
3. Add a new node in `nodes/`, wire it into `graph/__init__.py` or a new subgraph
4. Add the new step(s) to `_BOOKING_STEPS` or `_PNR_STEPS` in `graph/__init__.py`

### Add a Payment Gateway

Extend `nodes/payment.py` to call Stripe, Razorpay, or another provider after displaying the summary. The `done` node already calls `services/booking_save.py` for persistence.

### Add a New Channel

Create a new adapter file (e.g. `whatsapp_bot.py`) that:
1. Receives the user message
2. Loads or initialises `BookingState`
3. Calls `booking_graph.invoke(state)`
4. Sends `result["assistant_message"]` back to the user

No changes to any graph, node, or service file needed.

---

**Version**: 2.1  
**Last Updated**: 2026-06-27
