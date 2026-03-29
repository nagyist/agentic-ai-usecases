# 🏥 Doctor Appointment Booking Chatbot

A simple, end-to-end GenAI chatbot for booking doctor appointments at a clinic using **LangGraph** + **OpenAI** + **Streamlit**.

Read Complete Article [here](https://pub.towardsai.net/agentic-ai-project-build-a-customer-service-chatbot-for-a-clinic-9744ef4a5b25)

## Features

- ✅ Conversational appointment booking flow
- ✅ 5 doctors with different specialities
- ✅ Slot-based appointment selection
- ✅ LLM-only routing (no regex, no hard rules)
- ✅ State-driven conversation design
- ✅ Clickable options in Streamlit UI
- ✅ SQLite data persistence

## Project Structure

```
clinic-agent/
├── agents/
│   ├── booking_agent.py           # LangGraph agent with conversation flow
│   └── save_langgraph_flow.py     # Utility for saving LangGraph visualization
├── data/
│   └── db.py                      # SQLite database operations
├── services/
│   ├── booking_service.py         # Booking-related business logic
│   └── doctor_service.py          # Doctor-related business logic
├── test/
│   ├── test_agent.py              # Agent unit tests
│   └── test_service.py            # Service unit tests
├── ui/
│   └── chat_ui.py                 # Streamlit UI components
├── app.py                         # Main entry point
├── clinic-agent.ipynb             # Jupyter notebook for development
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
└── .env                           # Environment variables (add your OpenAI API key)
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Edit .env and add your OpenAI API key
   # The .env file should contain: OPENAI_API_KEY=your_api_key_here
   ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## How It Works

### Conversation Flow

1. **Greeting** → Bot welcomes user and shows specialities
2. **Select Speciality** → User picks a medical speciality
3. **Select Doctor** → Bot shows doctor info and available slots
4. **Select Time Slot** → User picks a time
5. **Confirm** → Review and confirm appointment
6. **Completed** → Booking confirmation with ID

### LLM-Based Routing

The agent uses OpenAI's GPT model for:
- **Intent classification** - Understanding what the user wants
- **Entity extraction** - Extracting specialities and time slots
- **State transitions** - Deciding next stage based on context

No regex or hard-coded rules - everything is handled by the LLM!

### Database Schema

**doctors** table:
- doctor_id, doctor_name, speciality, office_timing

**customers** table:
- customer_id, name, phone

**bookings** table:
- booking_id, doctor_id, customer_id, appointment_date, appointment_time, status

## Sample Conversation

```
User: Hi

Assistant: 👋 Welcome to CarePlus Clinic!
I can help you book an appointment with one of our doctors.
Please choose a speciality:
[General Physician] [Dermatologist] [Orthopedic] [Pediatrician] [ENT Specialist]

User: Dermatologist

Assistant: You've selected Dr. Neha Verma (Dermatologist).
Office timing is from 11:00-16:00.
Please select an available time slot:
[11:00 AM] [12:00 PM] [1:00 PM] [2:00 PM] [3:00 PM]

User: 1:00 PM

Assistant: Please review your appointment details:
Doctor: Dr. Neha Verma
Speciality: Dermatologist
Time: Today at 1:00 PM
Would you like to confirm this appointment?
[Confirm] [Cancel]

User: Confirm

Assistant: ✅ Appointment Confirmed!
Booking ID: BKG-102345
Doctor: Dr. Neha Verma
Time: Today at 1:00 PM
Thank you for choosing CarePlus Clinic.
```

## Available Doctors

| Doctor | Speciality | Office Hours |
|--------|-----------|--------------|
| Dr. Anil Sharma | General Physician | 10:00-14:00 |
| Dr. Neha Verma | Dermatologist | 11:00-16:00 |
| Dr. Rohit Mehta | Orthopedic | 09:00-13:00 |
| Dr. Kavita Rao | Pediatrician | 10:00-15:00 |
| Dr. Sanjay Iyer | ENT Specialist | 12:00-17:00 |

## Tech Stack

- **LangGraph** - Agent orchestration and state management
- **OpenAI GPT-4o-mini** - LLM for routing and extraction
- **Streamlit** - Web UI with clickable buttons
- **SQLite** - Simple data persistence
