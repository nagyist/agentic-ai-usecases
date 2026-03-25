"""SQLite database setup and operations for the clinic booking system."""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "clinic.db")


def get_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Initialize the database with tables and sample data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create doctors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            doctor_name TEXT NOT NULL,
            speciality TEXT NOT NULL,
            office_timing TEXT NOT NULL
        )
    """)
    
    # Create customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL
        )
    """)
    
    # Create bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            doctor_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors (doctor_id),
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
    """)
    
    # Insert sample doctors if not exists
    doctors = [
        ("D1", "Dr. Anil Sharma", "General Physician", "10:00-14:00"),
        ("D2", "Dr. Neha Verma", "Dermatologist", "11:00-16:00"),
        ("D3", "Dr. Rohit Mehta", "Orthopedic", "09:00-13:00"),
        ("D4", "Dr. Kavita Rao", "Pediatrician", "10:00-15:00"),
        ("D5", "Dr. Sanjay Iyer", "ENT Specialist", "12:00-17:00"),
    ]
    
    for doctor in doctors:
        cursor.execute(
            "INSERT OR IGNORE INTO doctors (doctor_id, doctor_name, speciality, office_timing) VALUES (?, ?, ?, ?)",
            doctor
        )
    
    conn.commit()
    conn.close()


def get_all_doctors():
    """Get all doctors from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()
    conn.close()
    return doctors


def get_doctor_by_speciality(speciality):
    """Get doctor by speciality."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM doctors WHERE LOWER(speciality) = LOWER(?)",
        (speciality,)
    )
    doctor = cursor.fetchone()
    conn.close()
    return doctor


def get_doctor_by_id(doctor_id):
    """Get doctor by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
    doctor = cursor.fetchone()
    conn.close()
    return doctor


def create_customer(customer_id, name, phone):
    """Create a new customer."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customers (customer_id, name, phone) VALUES (?, ?, ?)",
        (customer_id, name, phone)
    )
    conn.commit()
    conn.close()


def get_customer_by_phone(phone):
    """Get customer by phone number."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE phone = ?", (phone,))
    customer = cursor.fetchone()
    conn.close()
    return customer


def create_booking(booking_id, doctor_id, customer_id, appointment_date, appointment_time, status="Confirmed"):
    """Create a new booking."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookings (booking_id, doctor_id, customer_id, appointment_date, appointment_time, status) VALUES (?, ?, ?, ?, ?, ?)",
        (booking_id, doctor_id, customer_id, appointment_date, appointment_time, status)
    )
    conn.commit()
    conn.close()


def get_bookings_by_doctor_and_date(doctor_id, date_str):
    """Get all bookings for a doctor on a specific date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT appointment_time FROM bookings WHERE doctor_id = ? AND appointment_date = ? AND status = 'Confirmed'",
        (doctor_id, date_str)
    )
    bookings = cursor.fetchall()
    conn.close()
    return [b[0] for b in bookings]


def get_booking_by_id(booking_id):
    """Get booking by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,))
    booking = cursor.fetchone()
    conn.close()
    return booking


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized successfully.")
