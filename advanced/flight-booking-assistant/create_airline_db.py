import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import sqlite3
import os
import urllib.request

from faker import Faker


# Airport filter type: "all" | "selected"
# Full airport list (119): AGR AGX AJL ALA AMD ATQ AUH AYJ BAH BBI BDQ BEK BHO
#   BKK BLR BOM CCJ CCU CDP CGK CJB CMB CNN COK DAC DBR DED DEL DGH DHM DIB DIU
#   DMM DMU DOH DPS DXB GAU GAY GDB GOI GOP GOX GWL GYD HAN HBX HGI HJR HKG HKT
#   HSR HYD IDR IMF ISK IST IXA IXB IXC IXD IXE IXG IXJ IXL IXM IXR IXS IXU IXZ
#   JAF JAI JDH JED JGB JLR JRG JRH JSA KJB KLH KNU KTM KUL KWI LKO MAA MCT MLE
#   MYQ NAG NBO PAT PGH PNQ RDP RJA RKT RPR RQY RUH SAG SGN SHJ SHL SIN STV SXR
#   SXV TAS TBS TCR TIR TRV TRZ UDR VGA VNS VTZ
class DBConfig:
    # Reproducibility
    random_seed                  = 42

    # Date window — anchored to today so data is always futuristic
    schedule_start               = datetime.now()
    schedule_years               = 2
    flight_instance_years        = 2
    flight_instance_sample_weeks = 1

    # Airport filter
    # "all"      → every IndiGo airport (airport_list is ignored)
    # "selected" → only airports in airport_list
    airport_list_type            = "selected"
    airport_list                 = [
        "DEL", "BOM", "BLR", "MAA", "HYD", "CCU",   # major metros
        "AMD", "PNQ", "COK", "GOI", "JAI", "LKO",   # tier-2
        "NAG", "IXC", "PAT", "BBI", "SXR",
    ]

    # Volume
    num_customers                = 100
    num_bookings                 = 500
    # How many flights (from the schedule) to generate instances for.
    # Lower this to reduce FlightInstances rows and DB size.
    # None = use all flights in the schedule.
    max_flights_for_instances    = 20

    # Paths
    db_path                      = os.path.join(os.path.dirname(__file__), "indigo_airline.db")
    routes_url                   = (
        "https://raw.githubusercontent.com/alphaiterations/data-for-agents"
        "/main/airlines-data/airline_routes.json"
    )

    def seed_rng(self):
        np.random.seed(self.random_seed)
        random.seed(self.random_seed)

    @property
    def schedule_end(self):
        return self.schedule_start + timedelta(days=self.schedule_years * 365)


# Default config — modify fields directly or subclass to customise.
CONFIG = DBConfig()


# ============================================================================
# 1. FETCH airline_routes.json FROM GITHUB
# ============================================================================

def fetch_routes(cfg: DBConfig = CONFIG) -> dict:
    print(f"Fetching airline_routes.json from:\n  {cfg.routes_url}")
    with urllib.request.urlopen(cfg.routes_url) as response:
        routes_data = json.loads(response.read().decode())
    print("Routes data fetched successfully.")
    return routes_data


# ============================================================================
# 2. EXTRACT INDIGO (6E) ROUTES
# ============================================================================

def extract_indigo_routes(routes_data: dict, cfg: DBConfig = CONFIG) -> list[dict]:
    allowed = None if cfg.airport_list_type == "all" else set(cfg.airport_list)
    indigo_routes = []
    for airport_code, airport_data in routes_data.items():
        if allowed and airport_code not in allowed:
            continue
        if isinstance(airport_data, dict) and "routes" in airport_data:
            for route in airport_data["routes"]:
                if isinstance(route, dict) and "carriers" in route:
                    dest = route.get("iata")
                    if allowed and dest not in allowed:
                        continue
                    for carrier in route["carriers"]:
                        if carrier.get("iata") == "6E":
                            indigo_routes.append({
                                "origin": airport_code,
                                "destination": dest,
                                "distance_km": route.get("km", 0),
                                "duration_mins": route.get("min", 0),
                                "airline_code": "6E",
                                "airline_name": "IndiGo",
                            })
    airport_label = "all airports" if allowed is None else f"{len(allowed)} selected airports"
    print(f"IndiGo routes extracted ({airport_label}): {len(indigo_routes)}")
    return indigo_routes


# ============================================================================
# 3. CREATE DATABASE SCHEMA
# ============================================================================

def create_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.executescript("""
        DROP TABLE IF EXISTS FlightDelays;
        DROP TABLE IF EXISTS FlightInstances;
        DROP TABLE IF EXISTS PassengerBaggage;
        DROP TABLE IF EXISTS SpecialBaggage;
        DROP TABLE IF EXISTS Refunds;
        DROP TABLE IF EXISTS Payments;
        DROP TABLE IF EXISTS ItineraryLegs;
        DROP TABLE IF EXISTS Itineraries;
        DROP TABLE IF EXISTS Passengers;
        DROP TABLE IF EXISTS PNRs;
        DROP TABLE IF EXISTS Bookings;
        DROP TABLE IF EXISTS DaysOfOperation;
        DROP TABLE IF EXISTS FlightSchedule;
        DROP TABLE IF EXISTS Customers;
        DROP TABLE IF EXISTS ConnectionRules;
        DROP TABLE IF EXISTS AuditLog;

        CREATE TABLE Customers (
            customer_id       VARCHAR(20) PRIMARY KEY,
            first_name        VARCHAR(100),
            last_name         VARCHAR(100),
            email             VARCHAR(255) UNIQUE,
            phone_number      VARCHAR(20),
            date_of_birth     DATE,
            gender            VARCHAR(10),
            country_code      CHAR(2),
            city              VARCHAR(100),
            loyalty_program_id VARCHAR(20),
            customer_segment  VARCHAR(50),
            created_at        TIMESTAMP,
            updated_at        TIMESTAMP,
            is_synthetic      BOOLEAN DEFAULT 1
        );

        CREATE TABLE FlightSchedule (
            flight_id                VARCHAR(10) PRIMARY KEY,
            origin_airport_code      CHAR(3),
            destination_airport_code CHAR(3),
            departure_time           TIME,
            arrival_time             TIME,
            flight_duration_minutes  INTEGER,
            aircraft_type            VARCHAR(20),
            seat_capacity            INTEGER,
            status                   VARCHAR(50),
            created_at               TIMESTAMP
        );

        CREATE TABLE DaysOfOperation (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id      VARCHAR(10),
            day_of_week    INTEGER,
            effective_from DATE,
            effective_to   DATE,
            FOREIGN KEY (flight_id) REFERENCES FlightSchedule(flight_id)
        );

        CREATE TABLE PNRs (
            pnr_code    VARCHAR(6) PRIMARY KEY,
            customer_id VARCHAR(20),
            pnr_status  VARCHAR(50),
            issue_date  DATETIME,
            valid_until DATE,
            remarks     VARCHAR(500),
            created_at  TIMESTAMP,
            updated_at  TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
        );

        CREATE TABLE Bookings (
            booking_id        VARCHAR(20) PRIMARY KEY,
            pnr_code          VARCHAR(6),
            customer_id       VARCHAR(20),
            flight_id         VARCHAR(10),
            flight_date       DATE,
            total_passengers  INTEGER,
            booking_status    VARCHAR(50),
            booking_type      VARCHAR(50),
            total_fare        DECIMAL(10,2),
            tax_charges       DECIMAL(10,2),
            discount          DECIMAL(10,2),
            final_amount      DECIMAL(10,2),
            created_at        TIMESTAMP,
            updated_at        TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),
            FOREIGN KEY (pnr_code)    REFERENCES PNRs(pnr_code),
            FOREIGN KEY (flight_id)   REFERENCES FlightSchedule(flight_id)
        );

        CREATE TABLE Passengers (
            passenger_id     VARCHAR(20) PRIMARY KEY,
            booking_id       VARCHAR(20),
            first_name       VARCHAR(100),
            last_name        VARCHAR(100),
            date_of_birth    DATE,
            gender           VARCHAR(10),
            passport_number  VARCHAR(20),
            nationality      CHAR(2),
            passenger_type   VARCHAR(50),
            created_at       TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        );

        CREATE TABLE Itineraries (
            itinerary_id           VARCHAR(20) PRIMARY KEY,
            booking_id             VARCHAR(20),
            total_legs             INTEGER,
            journey_type           VARCHAR(50),
            total_duration_minutes INTEGER,
            created_at             TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        );

        CREATE TABLE ItineraryLegs (
            leg_id             VARCHAR(20) PRIMARY KEY,
            itinerary_id       VARCHAR(20),
            leg_number         INTEGER,
            flight_id          VARCHAR(10),
            flight_date        DATE,
            origin_airport     CHAR(3),
            destination_airport CHAR(3),
            departure_time     TIME,
            arrival_time       TIME,
            seat_number        VARCHAR(10),
            seat_class         VARCHAR(50),
            leg_status         VARCHAR(50),
            created_at         TIMESTAMP,
            FOREIGN KEY (itinerary_id) REFERENCES Itineraries(itinerary_id),
            FOREIGN KEY (flight_id)    REFERENCES FlightSchedule(flight_id)
        );

        CREATE TABLE PassengerBaggage (
            passenger_baggage_id VARCHAR(20) PRIMARY KEY,
            booking_id           VARCHAR(20),
            passenger_id         VARCHAR(20),
            baggage_type         VARCHAR(50),
            bag_weight_kg        DECIMAL(5,2),
            bag_dimensions_cm    VARCHAR(50),
            baggage_status       VARCHAR(50),
            baggage_tag_number   VARCHAR(20),
            created_at           TIMESTAMP,
            FOREIGN KEY (booking_id)   REFERENCES Bookings(booking_id),
            FOREIGN KEY (passenger_id) REFERENCES Passengers(passenger_id)
        );

        CREATE TABLE SpecialBaggage (
            special_baggage_id   VARCHAR(20) PRIMARY KEY,
            booking_id           VARCHAR(20),
            baggage_type         VARCHAR(50),
            item_description     VARCHAR(500),
            declared_value       DECIMAL(10,2),
            handling_instructions VARCHAR(500),
            created_at           TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        );

        CREATE TABLE FlightInstances (
            flight_instance_id VARCHAR(30) PRIMARY KEY,
            flight_id          VARCHAR(10),
            flight_date        DATE,
            scheduled_departure DATETIME,
            scheduled_arrival   DATETIME,
            actual_departure    DATETIME,
            actual_arrival      DATETIME,
            flight_status       VARCHAR(50),
            created_at          TIMESTAMP,
            FOREIGN KEY (flight_id) REFERENCES FlightSchedule(flight_id)
        );

        CREATE TABLE FlightDelays (
            delay_id            VARCHAR(20) PRIMARY KEY,
            flight_instance_id  VARCHAR(30),
            delay_category      VARCHAR(50),
            delay_reason        VARCHAR(500),
            delay_minutes       INTEGER,
            estimated_departure DATETIME,
            estimated_arrival   DATETIME,
            delay_status        VARCHAR(50),
            delay_announced_at  TIMESTAMP,
            created_at          TIMESTAMP,
            FOREIGN KEY (flight_instance_id) REFERENCES FlightInstances(flight_instance_id)
        );

        CREATE TABLE Payments (
            payment_id      VARCHAR(20) PRIMARY KEY,
            booking_id      VARCHAR(20),
            payment_amount  DECIMAL(10,2),
            payment_method  VARCHAR(50),
            payment_status  VARCHAR(50),
            transaction_id  VARCHAR(50),
            payment_gateway VARCHAR(50),
            created_at      TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        );

        CREATE TABLE Refunds (
            refund_id         VARCHAR(20) PRIMARY KEY,
            booking_id        VARCHAR(20),
            refund_reason     VARCHAR(50),
            refund_amount     DECIMAL(10,2),
            refund_percentage DECIMAL(5,2),
            refund_status     VARCHAR(50),
            refund_method     VARCHAR(50),
            refund_date       DATETIME,
            created_at        TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES Bookings(booking_id)
        );

        CREATE TABLE ConnectionRules (
            connection_id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_airport                   CHAR(3),
            destination_airport              CHAR(3),
            min_connection_time_domestic     INTEGER,
            min_connection_time_international INTEGER,
            turnaround_time_mins             INTEGER,
            created_at                       TIMESTAMP
        );

        CREATE TABLE AuditLog (
            log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type VARCHAR(50),
            entity_id   VARCHAR(50),
            action      VARCHAR(50),
            old_values  TEXT,
            new_values  TEXT,
            changed_by  VARCHAR(100),
            timestamp   DATETIME
        );
    """)
    conn.commit()
    print("Database schema created successfully.")


# ============================================================================
# 4. POPULATE FLIGHT SCHEDULE
# ============================================================================

def populate_flight_schedule(
    conn: sqlite3.Connection,
    indigo_routes: list[dict],
    cfg: DBConfig = CONFIG,
) -> list[str]:
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    unique_routes = {}
    for route in indigo_routes:
        key = (route["origin"], route["destination"])
        if key not in unique_routes:
            unique_routes[key] = route

    departure_times = ["06:00", "09:30", "12:00", "15:30", "18:00", "21:00"]
    aircraft_types = ["A320", "A321", "ATR72"]
    seat_capacities = {"A320": 180, "A321": 194, "ATR72": 70}

    flight_id_counter = 1
    for (origin, destination), route in unique_routes.items():
        duration_mins = route["duration_mins"]
        for dep_idx, dep_time in enumerate(departure_times):
            aircraft = aircraft_types[dep_idx % len(aircraft_types)]
            dep_h, dep_m = map(int, dep_time.split(":"))
            arr_h = (dep_h + duration_mins // 60) % 24
            arr_m = (dep_m + duration_mins % 60) % 60
            arr_time = f"{arr_h:02d}:{arr_m:02d}"
            flight_id = f"6E{flight_id_counter:04d}"

            cursor.execute(
                """INSERT INTO FlightSchedule
                   (flight_id, origin_airport_code, destination_airport_code,
                    departure_time, arrival_time, flight_duration_minutes,
                    aircraft_type, seat_capacity, status, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (flight_id, origin, destination, dep_time, arr_time,
                 duration_mins, aircraft, seat_capacities[aircraft], "active", now),
            )
            flight_id_counter += 1

    conn.commit()
    print(f"Flight schedule created: {flight_id_counter - 1} flights.")

    flights_df = pd.read_sql_query("SELECT flight_id FROM FlightSchedule", conn)
    flights_list = flights_df["flight_id"].tolist()

    effective_from = cfg.schedule_start.date().isoformat()
    effective_to = cfg.schedule_end.date().isoformat()
    rows = [
        (fid, day, effective_from, effective_to)
        for fid in flights_list
        for day in range(7)
    ]
    cursor.executemany(
        "INSERT INTO DaysOfOperation (flight_id, day_of_week, effective_from, effective_to) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    print("Days of operation inserted for all flights.")
    return flights_list


# ============================================================================
# 5. GENERATE CUSTOMERS
# ============================================================================

def populate_customers(
    conn: sqlite3.Connection,
    cfg: DBConfig = CONFIG,
) -> list[str]:
    num_customers = cfg.num_customers
    fake = Faker("en_IN")
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    customer_ids = []

    print(f"Generating {num_customers:,} synthetic customers...")
    batch = []
    for i in range(num_customers):
        cid = f"CUST{i+1:08d}"
        customer_ids.append(cid)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=75).isoformat()
        batch.append((
            cid,
            fake.first_name(), fake.last_name(),
            f"customer{i+1}@indigo.com",
            fake.phone_number()[:20],
            dob,
            random.choice(["M", "F", "Other"]),
            "IN",
            random.choice(["Delhi", "Mumbai", "Bangalore", "Chennai",
                           "Hyderabad", "Kolkata", "Pune", "Ahmedabad"]),
            f"6EREWARD{random.randint(100000, 999999)}",
            random.choice(["economy", "premium", "vip"]),
            now, now, 1,
        ))
        if len(batch) == 1000:
            cursor.executemany(
                """INSERT INTO Customers
                   (customer_id, first_name, last_name, email, phone_number,
                    date_of_birth, gender, country_code, city, loyalty_program_id,
                    customer_segment, created_at, updated_at, is_synthetic)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                batch,
            )
            conn.commit()
            print(f"  {i+1:,}/{num_customers:,} customers")
            batch = []

    if batch:
        cursor.executemany(
            """INSERT INTO Customers
               (customer_id, first_name, last_name, email, phone_number,
                date_of_birth, gender, country_code, city, loyalty_program_id,
                customer_segment, created_at, updated_at, is_synthetic)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            batch,
        )
        conn.commit()

    print(f"{num_customers:,} customers inserted.")
    return customer_ids


# ============================================================================
# 6. GENERATE BOOKINGS, PNRs, PASSENGERS & PAYMENTS
# ============================================================================

def populate_bookings(
    conn: sqlite3.Connection,
    customer_ids: list[str],
    flights_list: list[str],
    cfg: DBConfig = CONFIG,
) -> None:
    fake = Faker("en_IN")
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    num_bookings = cfg.num_bookings
    print(f"Generating {num_bookings:,} bookings...")

    for i in range(num_bookings):
        booking_id = f"BK{i+1:08d}"
        customer_id = random.choice(customer_ids)
        flight_id = random.choice(flights_list)
        flight_date = (
            cfg.schedule_start + timedelta(days=random.randint(0, cfg.schedule_years * 365))
        ).date().isoformat()

        num_pax = random.randint(1, 4)
        base_fare = random.randint(2000, 15000)
        total_fare = base_fare * num_pax
        tax = int(total_fare * 0.05)
        discount = int(total_fare * random.uniform(0, 0.15))
        final_amount = total_fare + tax - discount

        pnr_code = f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{i+1:06d}"
        booking_status = random.choice(["confirmed", "pending_payment", "cancelled"])
        pnr_status = "issued" if booking_status == "confirmed" else "pending"
        valid_until = (datetime.now() + timedelta(days=365)).date().isoformat()

        cursor.execute(
            """INSERT INTO PNRs (pnr_code, customer_id, pnr_status, issue_date, valid_until, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (pnr_code, customer_id, pnr_status, now, valid_until, now, now),
        )
        cursor.execute(
            """INSERT INTO Bookings
               (booking_id, pnr_code, customer_id, flight_id, flight_date,
                total_passengers, booking_status, booking_type, total_fare,
                tax_charges, discount, final_amount, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (booking_id, pnr_code, customer_id, flight_id, flight_date,
             num_pax, booking_status, "oneway", total_fare, tax, discount,
             final_amount, now, now),
        )

        itinerary_id = f"ITN{booking_id[2:]}"
        cursor.execute(
            """INSERT INTO Itineraries (itinerary_id, booking_id, total_legs, journey_type, total_duration_minutes, created_at)
               VALUES (?,?,?,?,?,?)""",
            (itinerary_id, booking_id, 1, "direct", 200, now),
        )

        for p in range(num_pax):
            passenger_id = f"PASS{booking_id[2:]}{p+1:02d}"
            dob = fake.date_of_birth(minimum_age=1, maximum_age=75).isoformat()
            cursor.execute(
                """INSERT INTO Passengers
                   (passenger_id, booking_id, first_name, last_name, date_of_birth,
                    gender, passport_number, nationality, passenger_type, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (passenger_id, booking_id, fake.first_name(), fake.last_name(),
                 dob, random.choice(["M", "F", "Other"]),
                 f"XXX{random.randint(1000, 9999)}", "IN",
                 "adult" if p == 0 else random.choice(["adult", "child"]), now),
            )
            cursor.execute(
                """INSERT INTO PassengerBaggage
                   (passenger_baggage_id, booking_id, passenger_id, baggage_type,
                    bag_weight_kg, baggage_status, baggage_tag_number, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (f"BAG{passenger_id}", booking_id, passenger_id, "checked",
                 round(random.uniform(10, 25), 1),
                 random.choice(["booked", "checked_in", "loaded", "delivered"]),
                 f"6E{random.randint(1000000, 9999999)}", now),
            )

        leg_id = f"LEG{booking_id[2:]}01"
        cursor.execute(
            """INSERT INTO ItineraryLegs
               (leg_id, itinerary_id, leg_number, flight_id, flight_date,
                origin_airport, destination_airport, departure_time, arrival_time,
                seat_number, seat_class, leg_status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (leg_id, itinerary_id, 1, flight_id, flight_date, "DEL", "BOM",
             "06:00", "08:30",
             f"{random.randint(1,20)}{random.choice(list('ABCDEF'))}",
             random.choice(["economy", "business"]), "confirmed", now),
        )

        cursor.execute(
            """INSERT INTO Payments
               (payment_id, booking_id, payment_amount, payment_method,
                payment_status, transaction_id, payment_gateway, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (f"PAY{booking_id[2:]}", booking_id, final_amount,
             random.choice(["credit_card", "debit_card", "upi", "netbanking"]),
             "success" if booking_status == "confirmed" else "pending",
             f"TXN{random.randint(1000000000, 9999999999)}",
             random.choice(["Razorpay", "PayU", "CCAvenue"]), now),
        )

        if (i + 1) % 5000 == 0:
            conn.commit()
            print(f"  {i+1:,}/{num_bookings:,} bookings")

    conn.commit()
    print(f"{num_bookings:,} bookings inserted.")


# ============================================================================
# 7. GENERATE FLIGHT INSTANCES & DELAYS
# ============================================================================

def populate_flight_instances(
    conn: sqlite3.Connection,
    flights_list: list[str],
    cfg: DBConfig = CONFIG,
) -> None:
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    instance_days = cfg.flight_instance_years * 365
    step_days = cfg.flight_instance_sample_weeks * 7
    print(f"Generating flight instances and delays ({cfg.flight_instance_years} years, sampled every {step_days}d)...")

    start = cfg.schedule_start
    delay_counter = 1

    sampled_flights = flights_list if cfg.max_flights_for_instances is None else flights_list[:cfg.max_flights_for_instances]
    print(f"  Generating instances for {len(sampled_flights)} flights...")

    for days_ahead in range(0, instance_days, step_days):
        current_date = start + timedelta(days=days_ahead)
        for flight_id in sampled_flights:
            row = cursor.execute(
                "SELECT departure_time, arrival_time FROM FlightSchedule WHERE flight_id=?",
                (flight_id,),
            ).fetchone()
            if row is None:
                continue

            dep_h, dep_m = map(int, row[0].split(":"))
            arr_h, arr_m = map(int, row[1].split(":"))
            sched_dep = current_date.replace(hour=dep_h, minute=dep_m)
            sched_arr = current_date.replace(hour=arr_h, minute=arr_m)
            if arr_h < dep_h:
                sched_arr += timedelta(days=1)

            instance_id = f"{flight_id}{current_date.strftime('%Y%m%d')}"
            cursor.execute(
                """INSERT INTO FlightInstances
                   (flight_instance_id, flight_id, flight_date,
                    scheduled_departure, scheduled_arrival, flight_status, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (instance_id, flight_id, current_date.date().isoformat(),
                 sched_dep.isoformat(), sched_arr.isoformat(), "scheduled", now),
            )

            if random.random() < 0.05:
                delay_mins = random.choice([15, 30, 45, 60, 90, 120])
                cursor.execute(
                    """INSERT INTO FlightDelays
                       (delay_id, flight_instance_id, delay_category, delay_reason,
                        delay_minutes, estimated_departure, estimated_arrival,
                        delay_status, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (f"DLY{delay_counter:08d}", instance_id,
                     random.choice(["weather", "mechanical", "crew", "air_traffic"]),
                     random.choice(["Heavy rain", "Aircraft maintenance",
                                    "Crew scheduling", "Air traffic control"]),
                     delay_mins,
                     (sched_dep + timedelta(minutes=delay_mins)).isoformat(),
                     (sched_arr + timedelta(minutes=delay_mins)).isoformat(),
                     "resolved", now),
                )
                delay_counter += 1

    conn.commit()
    print(f"Flight instances and {delay_counter - 1} delays inserted.")


# ============================================================================
# 8. SUMMARY
# ============================================================================

def print_summary(conn: sqlite3.Connection, cfg: DBConfig = CONFIG) -> None:
    tables = [
        "Customers", "FlightSchedule", "DaysOfOperation", "PNRs", "Bookings",
        "Passengers", "Itineraries", "ItineraryLegs", "PassengerBaggage",
        "FlightInstances", "FlightDelays", "Payments",
    ]
    print("\n" + "=" * 60)
    print("DATABASE SUMMARY - INDIGO AIRLINE BOOKING SYSTEM")
    print("=" * 60)
    total = 0
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        total += count
        print(f"  {table:<30} {count:>10,}")
    print("-" * 60)
    print(f"  {'TOTAL':<30} {total:>10,}")
    db_mb = os.path.getsize(cfg.db_path) / (1024 * 1024)
    print(f"\nDatabase file : {cfg.db_path}")
    print(f"Database size : {db_mb:.2f} MB")
    print("=" * 60)


# ============================================================================
# MAIN
# ============================================================================

def main(cfg: DBConfig = CONFIG) -> None:
    cfg.seed_rng()
    print(f"Config: seed={cfg.random_seed}, start={cfg.schedule_start.date()}, "
          f"schedule_years={cfg.schedule_years}, customers={cfg.num_customers:,}, "
          f"bookings={cfg.num_bookings:,}")

    if os.path.exists(cfg.db_path):
        os.remove(cfg.db_path)
        print(f"Removed existing database: {cfg.db_path}")

    routes_data = fetch_routes(cfg)
    indigo_routes = extract_indigo_routes(routes_data, cfg)

    conn = sqlite3.connect(cfg.db_path)
    try:
        create_schema(conn)
        flights_list = populate_flight_schedule(conn, indigo_routes, cfg)
        customer_ids = populate_customers(conn, cfg)
        populate_bookings(conn, customer_ids, flights_list, cfg)
        populate_flight_instances(conn, flights_list, cfg)
        print_summary(conn, cfg)
    finally:
        conn.close()

    print("\nDone. Database is ready.")


if __name__ == "__main__":
    main()
