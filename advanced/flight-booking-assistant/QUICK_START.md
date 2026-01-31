# Quick Start Guide - Indigo Flight Booking Assistant

## 🚀 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install langgraph langchain-core langchain-openai
```

### Step 2: Open the Notebook
```
/Users/vijendra/agentic-ai-usecases/advanced/flight-booking-assistant/flight_booking_langgraph.ipynb
```

### Step 3: Run All Cells
Click "Run All" or press Shift+Enter on each cell sequentially.

### Step 4: Choose Your Interaction Mode

#### Option A: Automated Demo (Fastest)
```python
final_state = run_flight_booking_assistant()
```
This runs a complete booking flow with pre-filled test data in ~30 seconds.

#### Option B: Interactive Chat (Most Fun)
```python
start_interactive_chat()

# Then type:
chat("Book a flight")
chat("Mumbai")
chat("Jaipur")
chat("10th Feb")
chat("One-way")
chat("1 adult")
chat("No child")
chat("Yes")
chat("Flight 2")
chat("Yes")
chat("Yes")
chat("Mr. John Doe")
chat("john@example.com")
chat("9876543210")
```

## 📖 Sample Conversation Scripts

### Script 1: Jaipur to Mumbai (Used in Demo)
```
Destination: Mumbai
Origin: Jaipur
Date: 10th Feb
Journey Type: One-way
Adults: 1
Children: No
Flight: 2 (6E4712 @ 9:30)
Name: Mr. Vijendra Jain
Email: vijendra.1893@gmail.com
Phone: 9876543210
```

### Script 2: Delhi to Bangalore
```
Destination: Bangalore
Origin: Delhi
Date: 15th Feb
Journey Type: One-way
Adults: 2
Children: 1
Flight: 1
Name: Mr. Raj Kumar, Mrs. Priya Kumar
Email: rajkumar@example.com
Phone: 9876543211
```

### Script 3: Pune to Hyderabad
```
Destination: Hyderabad
Origin: Pune
Date: 20th Feb
Journey Type: One-way
Adults: 3
Children: No
Flight: 3 (Cheapest option)
Names: Mr. Smith, Mr. Johnson, Mr. Williams
Email: group@example.com
Phone: 9876543212
```

## 🎯 Expected Output

After completing the booking flow, you should see:

```
======================================================================
🛫 INDIGO FLIGHT BOOKING ASSISTANT DEMO 🛫
======================================================================

👤 User (1): Book a flight ticket
🤖 Assistant: Please let us know your destination

[... conversation continues ...]

👤 User (14): 9876543210
🤖 Assistant: Review Your Booking
-----------------------------------

JAI ↔️ BOM (ONWARD)

🗓️ 10-02-2026 

Mr Vijendra Jain

✈️ Onward flight - 10-02-2026 
6E4712
09:30  - 10:20  (1 h 50 min) 
Nonstop 
 Jaipur International Airport ➡️ Chhatrapati Shivaji International Airport

Payment Details
-----------------------------------
Adult(s)         1 x ₹6031    ₹6031
-----------------------------------
Total                     ₹6031

✅ Booking process completed!

======================================================================
📊 BOOKING SUMMARY
======================================================================
Origin: JAI
Destination: BOM
Travel Date: 10th Feb
Passengers: 1 adult(s), 0 child(ren)
Selected Flight: 6E4712
Passenger Names: Mr. Vijendra Jain
Email: vijendra.1893@gmail.com
Phone: 9876543210
PNR Code: OF7XJ0
Booking Confirmed: ✅ Yes
======================================================================
```

## 🔍 Testing Tips

### Tip 1: Skip to Flight Selection
```python
# Manually set state to test flight selection
chat_state['current_step'] = 'flight_selection'
chat_state['available_flights'] = get_flights('JAI', 'BOM')
chat_state['origin'] = 'JAI'
chat_state['destination'] = 'BOM'
chat("Flight 1")
```

### Tip 2: Debug State
```python
# Print current state
print(json.dumps({k: str(v) if not isinstance(v, (list, dict)) else v 
                  for k, v in chat_state.items()}, indent=2))
```

### Tip 3: Test Database
```python
# Query flights directly
flights = get_flights('JAI', 'BOM')
for flight in flights:
    print(f"{flight['flight_id']}: {flight['departure_time']} - {flight['arrival_time']}")
```

## 🛫 Available Routes

**Currently working routes from database:**
- JAI (Jaipur) ↔ BOM (Mumbai) - 6 flights
- JAI (Jaipur) ↔ DEL (Delhi) - Available
- Plus many more...

## 🎓 What You'll Learn

1. **State Management** - How to manage conversation state
2. **Database Queries** - SQLite integration with Python
3. **Natural Language Processing** - Simple regex-based parsing
4. **Conversation Design** - Multi-turn dialogue flows
5. **Error Handling** - Input validation and recovery

## ⚠️ Common Issues & Solutions

### Issue: "Database not found"
**Solution:** Ensure `indigo_airline.db` exists in the same directory as the notebook.

### Issue: "ModuleNotFoundError: No module named 'langgraph'"
**Solution:** Run `pip install langgraph langchain-core` in terminal.

### Issue: Empty flights list
**Solution:** Make sure origin and destination airport codes are correct (JAI, BOM, DEL, etc.)

### Issue: Chat history gets confused
**Solution:** Run `start_interactive_chat()` again to reset the state.

## 💡 Customization Ideas

### Add New Airport
```python
AIRPORT_CODES['hyderabad'] = 'HYD'
AIRPORT_NAMES['HYD'] = 'Rajiv Gandhi International Airport'
```

### Change Base Fare
```python
base_fare = 4500  # Change from 6031
```

### Add New Service Option
```python
elif 'refund' in user_input_lower:
    state['service_selected'] = 'refund'
    next_msg = "Please provide your PNR code for refund..."
```

## 🚀 Next Steps

1. **Test the automated demo** - `run_flight_booking_assistant()`
2. **Try interactive mode** - `start_interactive_chat()` + `chat(...)`
3. **Read full documentation** - See `FLIGHT_BOOKING_README.md`
4. **Explore the code** - Each function is well-commented
5. **Customize for your needs** - Add more airports, airlines, etc.

## 📞 Support

For issues or questions, refer to:
- `FLIGHT_BOOKING_README.md` - Complete documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- Inline code comments in the notebook

---

**Happy Booking! 🛫**

Have fun with your Indigo Flight Booking Assistant!
