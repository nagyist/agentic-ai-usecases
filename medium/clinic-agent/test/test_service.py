from pathlib import Path
import sys

# Allow running this file directly: `python test/test_service.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.doctor_service import get_specialities_list, generate_time_slots
from services.booking_service import confirm_booking

# Get all specialities
specialities = get_specialities_list()
print("Available specialities:", specialities)

# Generate time slots for a doctor (11:00 AM - 4:00 PM)
slots = generate_time_slots("11:00-16:00")
print("Available slots:", slots)

# Confirm a booking
booking_id = confirm_booking(
    doctor_id="D1",
    customer_name="John Doe",
    customer_phone="9876543210",
    time_slot="2:00 PM"
)
print(f"Booking confirmed: {booking_id}")