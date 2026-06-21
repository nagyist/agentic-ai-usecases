# Indigo Flight Booking Assistant

A production-grade conversational AI agent for IndiGo Airlines, built with LangGraph and OpenAI GPT-4o-mini. Supports flight booking (one-way and round-trip), web check-in, and flight status enquiries across Streamlit web and Telegram channels.

---

## Project Structure

```
flight-booking-assistant/
├── app.py                       ← Streamlit web UI (primary entry point)
├── telegram_bot.py              ← Telegram bot adapter
├── graph.py                     ← LangGraph state machine (11 nodes)
├── state.py                     ← TypedDict state definitions
├── config.py                    ← City/airport mappings, session config
├── constants.py                 ← Step, Intent, Process enums
├── create_airline_db.py         ← Database creation script
├── agents/                      ← LLM-based agents (GPT-4o-mini)
│   ├── router.py                ← Intent detection
│   ├── information_extractor.py ← Slot & passenger info extraction
│   ├── city_lookup.py           ← City name → IATA code resolution
│   ├── confirmation.py          ← Pre-search confirmation handler
│   └── flight_selection.py      ← Flight choice parsing
├── nodes/                       ← LangGraph node implementations
│   ├── conversation_driver.py   ← Question sequencing, slot collection
│   ├── slot_validator.py        ← Date/passenger count validation
│   ├── payment.py               ← Booking summary + payment display
│   ├── done.py                  ← Post-booking completion message
│   └── post_confirmation.py     ← Flight confirm, WhatsApp, names, email
├── services/                    ← Business logic
│   ├── flight_search.py         ← SQLite flight queries
│   └── pnr_lookup.py            ← PNR fetch + status/check-in formatting
├── utils/                       ← Shared utilities
│   ├── llm.py                   ← OpenAI API calls + token logging
│   ├── db.py                    ← SQLite connection helpers
│   ├── prompts.py               ← LLM prompt templates
│   └── formatting.py            ← Date and flight display formatting
├── indigo_airline.db            ← SQLite database (17 tables, pre-loaded)
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- OpenAI API key (set as `OPENAI_API_KEY` in `.env` or environment)

### Installation

```bash
cd advanced/flight-booking-assistant
pip install -r requirements.txt
```

Create a `.env` file at the project root:
```
OPENAI_API_KEY=sk-...
```

### Run the Streamlit Web App

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The assistant greets you and is ready to chat.

### Run the Telegram Bot

Set your bot token in `.env`:
```
TELEGRAM_BOT_TOKEN=<your-bot-token>
```

Then:
```bash
python telegram_bot.py
```

---

## Supported Processes

The assistant detects intent from the user's first message and routes to the appropriate process.

| Process | Trigger | Description |
|---------|---------|-------------|
| `book_flight` | "Book a ticket", "I want to fly to Delhi" | Full multi-turn booking (one-way or round-trip) |
| `web_checkin` | "Web check-in", "Check in for my flight" | PNR lookup → check-in eligibility display |
| `flight_status` | "Flight status", "Where is my flight" | PNR lookup → live flight status display |

> Switching processes mid-session is blocked. Type **"exit"** to reset and start a new process.

---

## Architecture

### LangGraph State Machine

The entire conversation is managed as a single TypedDict state flowing through an 11-node LangGraph graph.

```
START
  └─ Router (LLM intent detection)
       ├─ book_flight ──→ Information Extractor (LLM slot extraction)
       │                       └─ Slot Validator (date/passenger validation)
       │                            └─ City Lookup (LLM: city → IATA)
       │                                 └─ Conversation Driver (collect missing slots)
       │                                      └─ Confirmation (LLM: yes/no)
       │                                           └─ Flight Search (SQLite query)
       │                                                └─ Flight Selection (LLM: user picks flight)
       │                                                     └─ Post-Confirmation
       │                                                     │    (flight confirm → WhatsApp consent
       │                                                     │     → passenger names → email)
       │                                                     └─ Payment (summary display)
       │                                                          └─ Done
       ├─ web_checkin ─→ PNR Lookup → Done
       └─ flight_status → PNR Lookup → Done
```

### LLM Call Points (GPT-4o-mini)

| Agent | Purpose |
|-------|---------|
| `router.py` | Classify intent from user message |
| `information_extractor.py` | Extract origin, destination, date, passengers, names, email |
| `city_lookup.py` | Resolve city names to IATA codes, suggest candidates on mismatch |
| `confirmation.py` | Parse yes/no from free-text confirmation responses |
| `flight_selection.py` | Parse user's flight choice from natural language |

All LLM calls use JSON schema mode and are logged with token counts and latencies in `utils/llm.py`.

### Error Handling & Retry Logic

- Each slot tracks attempt count via `slot_attempts` dict in state
- After **3 failed attempts** on any field, the session terminates with a customer care message
- Name collection has a separate attempt counter
- Session TTL is **30 minutes** (configurable via `SESSION_TTL_SECONDS` in `config.py`)

---

## Conversation Flow (Book Flight)

```
User: "Book a flight to Mumbai"
  └─ Router → book_flight
       └─ Extractor → destination=BOM extracted
            └─ Conversation Driver → asks for origin
User: "From Jaipur"
  └─ Extractor → origin=JAI extracted
       └─ Conversation Driver → asks for travel date
User: "15th July"
  └─ Slot Validator → date valid
       └─ Conversation Driver → asks one-way or round-trip
...
  └─ Confirmation → "Confirm JAI→BOM, 15 Jul, 1 adult?"
User: "Yes"
  └─ Flight Search → shows available flights
User: "Flight 2"
  └─ Flight Selection → selects 6E4712
       └─ Post-Confirmation → confirm flight, WhatsApp consent, collect names + email
            └─ Payment → displays booking summary with PNR
                 └─ Done
```

For **round-trip**, the flow repeats the flight search and selection step for the return leg.

---

## Available Routes & Airport Codes

The database contains 12 real IndiGo routes. Example routes:

- **JAI ↔ BOM** (Jaipur ↔ Mumbai)
- **JAI ↔ DEL** (Jaipur ↔ Delhi)
- **BOM ↔ BLR** (Mumbai ↔ Bangalore)
- **DEL ↔ HYD** (Delhi ↔ Hyderabad)

Supported cities (resolved via LLM + `config.py` mapping):

| City | Code | Airport |
|------|------|---------|
| Delhi / New Delhi | DEL | Indira Gandhi International Airport |
| Mumbai / Bombay | BOM | Chhatrapati Shivaji Maharaj International Airport |
| Bangalore / Bengaluru | BLR | Kempegowda International Airport |
| Jaipur | JAI | Jaipur International Airport |
| Hyderabad | HYD | Rajiv Gandhi International Airport |
| Kolkata / Calcutta | CCU | Netaji Subhas Chandra Bose International Airport |
| Chennai / Madras | MAA | Chennai International Airport |
| Kochi / Cochin | COK | Cochin International Airport |
| Pune | PNQ | Pune Airport |
| Goa / Panaji | GOI | Goa International Airport |
| Lucknow | LKO | Chaudhary Charan Singh International Airport |

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

Add entries to `config.py`:
```python
CITY_TO_CODE["ahmedabad"] = "AMD"
CODE_TO_AIRPORT["AMD"] = "Sardar Vallabhbhai Patel International Airport"
```

### Add a New Process

1. Add the intent to `constants.py`:
   ```python
   class Intent:
       LUGGAGE_TRACKING = "luggage_tracking"
   ```
2. Add routing logic in `agents/router.py` prompt
3. Add a new node in `nodes/` and wire it into `graph.py`

### Modify Pricing

Dynamic pricing is calculated in `services/flight_search.py`. Base fare is `2500 + variation`; change the base or formula there.

### Add a Payment Gateway

Extend `nodes/payment.py` to call Stripe, Razorpay, or another provider after displaying the summary.

---

## Learning Topics

This project demonstrates:

1. **LangGraph state machines** — TypedDict state, conditional edges, multi-node routing
2. **LLM-driven NLU** — intent classification, slot extraction, entity resolution with JSON schema mode
3. **Multi-channel architecture** — shared graph invoked by both Streamlit and Telegram adapters
4. **Conversational error recovery** — per-field retry tracking, graceful degradation
5. **SQLite integration** — flight search, PNR lookup, dynamic pricing

---

**Version**: 2.0
**Last Updated**: 2026-06-14
