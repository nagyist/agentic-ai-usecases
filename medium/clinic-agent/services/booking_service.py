"""Service layer for booking-related operations."""

import uuid
from datetime import datetime
from data.db import (
    create_customer,
    create_booking,
    get_customer_by_phone,
    get_bookings_by_doctor_and_date,
    get_booking_by_id
)
from services.doctor_service import parse_time_slot


def get_or_create_customer(name, phone):
    """Get existing customer or create new one."""
    customer = get_customer_by_phone(phone)
    if customer:
        return customer[0]  # Return customer_id
    
    customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
    create_customer(customer_id, name, phone)
    return customer_id


def get_available_slots(doctor_id, office_timing):
    """Get available time slots for a doctor for today.
    
    Args:
        doctor_id: Doctor ID
        office_timing: Office timing string like "11:00-16:00"
    
    Returns:
        List of available time slots
    """
    from services.doctor_service import generate_time_slots
    
    today = datetime.now().strftime("%Y-%m-%d")
    all_slots = generate_time_slots(office_timing)
    
    # Get booked slots
    booked_times = get_bookings_by_doctor_and_date(doctor_id, today)
    
    # Filter out booked slots
    available = []
    for slot in all_slots:
        slot_24h = parse_time_slot(slot)
        if slot_24h not in booked_times:
            available.append(slot)
    
    return available


def confirm_booking(doctor_id, customer_name, customer_phone, time_slot, appointment_date=None):
    """Confirm a booking.
    
    Args:
        doctor_id: Doctor ID
        customer_name: Customer name
        customer_phone: Customer phone
        time_slot: Time slot like "1:00 PM"
        appointment_date: Optional date in YYYY-MM-DD format. Defaults to today.
    
    Returns:
        Booking ID
    """
    # Get or create customer
    customer_id = get_or_create_customer(customer_name, customer_phone)
    
    # Generate booking ID
    booking_id = f"BKG-{uuid.uuid4().hex[:6].upper()}"
    
    # Format appointment time
    if not appointment_date:
        appointment_date = datetime.now().strftime("%Y-%m-%d")
    appointment_time = parse_time_slot(time_slot)
    
    # Create booking
    create_booking(booking_id, doctor_id, customer_id, appointment_date, appointment_time)
    
    return booking_id


def get_booking_details(booking_id):
    """Get booking details by ID."""
    booking = get_booking_by_id(booking_id)
    if booking:
        return {
            "booking_id": booking[0],
            "doctor_id": booking[1],
            "customer_id": booking[2],
            "appointment_date": booking[3],
            "appointment_time": booking[4],
            "status": booking[5]
        }
    return None