"""Service layer for doctor-related operations."""

from data.db import get_all_doctors, get_doctor_by_speciality, get_doctor_by_id


def get_specialities_list():
    """Get list of all specialities."""
    doctors = get_all_doctors()
    # Return unique specialities
    return list(dict.fromkeys([doc[2] for doc in doctors]))


def get_doctor_info(speciality):
    """Get doctor information by speciality."""
    doctor = get_doctor_by_speciality(speciality)
    if doctor:
        return {
            "doctor_id": doctor[0],
            "doctor_name": doctor[1],
            "speciality": doctor[2],
            "office_timing": doctor[3]
        }
    return None


def get_doctor_info_by_id(doctor_id):
    """Get doctor information by ID."""
    doctor = get_doctor_by_id(doctor_id)
    if doctor:
        return {
            "doctor_id": doctor[0],
            "doctor_name": doctor[1],
            "speciality": doctor[2],
            "office_timing": doctor[3]
        }
    return None


def generate_time_slots(office_timing):
    """Generate hourly time slots from office timing string.
    
    Args:
        office_timing: String like "11:00-16:00"
    
    Returns:
        List of time slots like ["11:00 AM", "12:00 PM", ...]
    """
    start_time, end_time = office_timing.split("-")
    start_hour = int(start_time.split(":")[0])
    end_hour = int(end_time.split(":")[0])
    
    slots = []
    for hour in range(start_hour, end_hour):
        if hour < 12:
            suffix = "AM"
            display_hour = hour if hour > 0 else 12
        elif hour == 12:
            suffix = "PM"
            display_hour = 12
        else:
            suffix = "PM"
            display_hour = hour - 12
        slots.append(f"{display_hour}:00 {suffix}")
    
    return slots


def parse_time_slot(slot_str):
    """Parse time slot string to 24-hour format.
    
    Args:
        slot_str: String like "1:00 PM"
    
    Returns:
        String like "13:00"
    """
    time_part, suffix = slot_str.split(" ")
    hour, minute = time_part.split(":")
    hour = int(hour)
    
    if suffix == "PM" and hour != 12:
        hour += 12
    elif suffix == "AM" and hour == 12:
        hour = 0
    
    return f"{hour:02d}:{minute}"