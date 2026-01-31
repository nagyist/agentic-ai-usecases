# Indigo Flight Booking Assistant with LangGraph

A conversational AI-powered flight booking assistant built with **LangGraph** that integrates with the Indigo Airline SQLite database. The assistant guides users through the complete flight booking process with a multi-turn conversation flow.

## 🎯 Features

✅ **Multi-turn Conversational Flow** - Guided booking process with intelligent routing  
✅ **Database Integration** - Real flight data from `indigo_airline.db`  
✅ **Flight Search & Filtering** - Query available flights by route, date, and aircraft  
✅ **Passenger Management** - Collect and validate passenger information  
✅ **Booking Confirmation** - Generate PNR codes and provide booking summaries  
✅ **WhatsApp Consent** - Privacy policy compliance  
✅ **Email & Phone Validation** - Ensure data quality  

## 📋 Conversation Flow

The assistant follows a structured booking journey:

```
1. Greeting → Service Selection
   ↓
2. Destination Input → Origin Input
   ↓
3. Travel Date Input → Return Date (or One-way confirmation)
   ↓
4. Passenger Count Input (Adults & Children)
   ↓
5. Booking Review & Confirmation
   ↓
6. Flight Search & Display (6E-5035, 6E-4711, etc.)
   ↓
7. Flight Selection & Confirmation
   ↓
8. WhatsApp Consent
   ↓
9. Passenger Details (Names)
   ↓
10. Email & Phone Collection
    ↓
11. Payment Review & Booking Summary
    ↓
12. PNR Generation & Confirmation
```

## 🗄️ Database Schema

The assistant queries the following key tables:

### `FlightSchedule`
- `flight_id`: Flight identifier (e.g., 6E4711)
- `origin_airport_code`: Departure airport (JAI, BOM, DEL, etc.)
- `destination_airport_code`: Arrival airport
- `departure_time`: Scheduled departure time
- `arrival_time`: Scheduled arrival time
- `flight_duration_minutes`: Flight duration
- `aircraft_type`: Aircraft model (A320, A321, ATR72)
- `seat_capacity`: Total seats available
- `status`: Flight status (active, inactive)

### `Customers`, `Bookings`, `Passengers`, `PNRs`
- Store customer, booking, and passenger information

## 🚀 Getting Started

### Prerequisites

```bash
pip install langgraph langchain-core langchain-openai sqlite3
```

### Running the Assistant

1. **Open the notebook**: `flight_booking_langgraph.ipynb`

2. **Run all cells** in order to initialize the assistant

3. **Interactive Chat**:
   ```python
   # Start the assistant
   start_interactive_chat()
   
   # Chat with the assistant
   chat("Book a flight ticket")
   chat("Mumbai")
   chat("Jaipur")
   chat("10th Feb")
   # ... continue the conversation
   ```

4. **Automated Demo**:
   ```python
   final_state = run_flight_booking_assistant()
   ```

## 📊 State Management

The `BookingState` TypedDict tracks:

```python
{
    'messages': List[BaseMessage],           # Conversation history
    'current_step': str,                     # Current stage in booking
    'service_selected': str,                 # 'book_flight', 'flight_status', etc.
    'origin': str,                           # Airport code (JAI)
    'destination': str,                      # Airport code (BOM)
    'travel_date': str,                      # Travel date (10th Feb)
    'journey_type': str,                     # 'oneway' or 'roundtrip'
    'adults': int,                           # Number of adult passengers
    'children': int,                         # Number of children
    'selected_flight': str,                  # Flight ID (6E4712)
    'passenger_names': List[str],            # Passenger names
    'email': str,                            # Passenger email
    'phone': str,                            # Contact phone
    'pnr': str,                              # Generated PNR code
    'booking_confirmed': bool,               # Booking status
    'available_flights': List[Dict]          # Retrieved flights
}
```

## 🛫 Sample Conversation

```
User: Hello
Assistant: Hello! I'm 6ESkai, your friendly AI assistant from Indigo.
How can I help you with our services today?
- Book a flight ticket
- Flight Status
- Web Check in

User: Book a flight ticket
Assistant: Please let us know your destination

User: Mumbai
Assistant: Please let us know your starting city

User: Jaipur
Assistant: Which day is your journey starting on? (eg. 10th Feb, Feb 10)

User: 10th Feb
Assistant: On which date will you conclude your travels?
- [option] One-way only

User: One-way only
Assistant: Can you please tell me the number of passengers?
eg. 2 adults, 1 child

User: 1 adult
Assistant: Just to confirm how many child passengers are there?
[option] No child passengers

User: No child passengers
Assistant: Congratulations you are receiving a discounted fare by Indigo with our 6Exclusive offer..
Please review your travel details

Departure - Jaipur International Airport (JAI)
Destination: Chhatrapati Shivaji International Airport (BOM)
Travel Date: 10th Feb
Passenger Count - 1 Adult

Please review and confirm the booking specifics (yes/no)

User: Yes
Assistant: I found 6 onward flights for you on 10 February 2026
-----
Flight 1
06:00 -- 1h50min -- 07:50
Starts at rs5500
Non-stop
6E4711
-----
Flight 2
09:30 -- 1h50min -- 10:20
Starts at rs6000
Non-stop
6E4712
...

User: Flight 2
Assistant: please review onward flight details
Departure: (Jaipur International Airport) JAI
Destination: Chhatrapati Shivaji International Airport (BOM)
Travel Date: 10th Feb 2026
09:30 -- 1h50min -- 10:20
Starts at rs6031
Non-stop
6E4712

Please review and confirm your Indigo 6E4712 flight

User: Yes
Assistant: To keep you informed about our products and services, we would like your consent to communicate with you on Whatsapp.
By confirming Yes, you agree to IndiGo's Privacy Policy...

User: Yes
Assistant: Okay, continuing with the process,
Can you please tell me the full name of all the passengers

User: Mr. Vijendra Jain
Assistant: Please provide your email address in the correct format.

User: vijendra.1893@gmail.com
Assistant: Please provide your contact phone number (10 digits)

User: 9876543210
Assistant: Review Your Booking
-----------------------------------
JAI ↔️ BOM (ONWARD)
🗓️ 10-02-2026 
Mr Vijendra Jain
✈️ Onward flight - 10-02-2026 
6E4712
09:30 - 10:20 (1h 50min)
Nonstop 
Jaipur International Airport ➡️ Chhatrapati Shivaji International Airport

Payment Details
-----------------------------------
Adult(s)         1 x ₹6,031    ₹6,031
-----------------------------------
Total                     ₹6,031

PNR Code: OF7XJ0
```

## 🔧 Key Functions

### Database Operations
- `get_db_connection()` - Establish SQLite connection
- `get_flights(origin, destination)` - Query flights from database
- `format_flight_list(flights)` - Format flights for display

### Conversation Handlers
- `greet_user()` - Initial greeting
- `process_service_selection()` - Route to service type
- `get_destination()` - Capture destination
- `get_origin()` - Capture origin
- `get_travel_date()` - Capture travel date
- `get_passenger_count()` - Parse passenger information
- `confirm_booking_details()` - Review and confirm booking
- `select_flight()` - Handle flight selection
- `get_passenger_names()` - Collect passenger names
- `get_email()` - Validate email address
- `get_phone()` - Validate phone number
- `show_payment_review()` - Display payment summary

### State Management
- `create_initial_state()` - Initialize conversation state
- `process_user_input()` - Route input to appropriate handler
- `run_flight_booking_assistant()` - Run automated demo
- `start_interactive_chat()` - Initialize interactive session
- `chat()` - Send message in interactive mode

## 📍 Supported Routes

The database includes flights between major Indian airports:

**Origin Codes**: JAI (Jaipur), DEL (Delhi), BOM (Mumbai), BLR (Bangalore), HYD (Hyderabad), CCU (Kolkata), COK (Kochi), PNQ (Pune)

**Current Sample Routes**:
- JAI ↔ BOM (Jaipur to Mumbai) - 6 flights daily
- JAI ↔ DEL (Jaipur to Delhi)
- And many more...

## 💾 Database Location

```
/Users/vijendra/agentic-ai-usecases/advanced/flight-booking-assistant/indigo_airline.db
```

## 🎓 Learning Objectives

This project demonstrates:
- ✅ Multi-turn conversation management with state machines
- ✅ Database integration with flight search queries
- ✅ Natural language understanding for route/date/passenger parsing
- ✅ Input validation and error handling
- ✅ PNR generation and booking confirmation
- ✅ LangGraph state-based architecture
- ✅ Structured conversation flows

## 🚧 Future Enhancements

- [ ] LLM-powered natural language understanding (using Claude/GPT)
- [ ] Round-trip flight support
- [ ] Multi-city journey planning
- [ ] Seat selection interface
- [ ] Real-time fare updates
- [ ] Loyalty program integration
- [ ] Payment gateway integration
- [ ] SMS/Email confirmation
- [ ] Booking modification & cancellation
- [ ] Flight status tracking

## 📝 Notes

- The assistant uses rule-based routing for simplicity
- Prices are dynamically generated based on flight order
- PNR codes are randomly generated (6-character alphanumeric)
- Flight durations are retrieved from the database
- All timestamps are in 24-hour format

## 📄 License

This project is part of the agentic-ai-usecases repository.

---

**Created**: January 31, 2026  
**Notebook**: `flight_booking_langgraph.ipynb`  
**Database**: `indigo_airline.db`
