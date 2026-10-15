"""Demo data so a fresh environment shows a realistic dashboard.

Only runs when SEED_DEMO_DATA=true and the database has no doctors yet.
Appointments are placed relative to "today" in the clinic's timezone.
"""

import logging
import random
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .clinic_time import clinic_today, clinic_zone
from .models import Appointment, Doctor, Patient

log = logging.getLogger("cliniccare.seed")

DOCTORS = [
    ("Dr. Ananya Rao", "Cardiology", "ananya.rao", "101"),
    ("Dr. Vikram Mehta", "Orthopedics", "vikram.mehta", "102"),
    ("Dr. Priya Nair", "Pediatrics", "priya.nair", "201"),
    ("Dr. Arjun Iyer", "Dermatology", "arjun.iyer", "202"),
    ("Dr. Kavya Reddy", "General Medicine", "kavya.reddy", "103"),
    ("Dr. Rohan Kapoor", "ENT", "rohan.kapoor", "203"),
]

PATIENTS = [
    ("Aarav Sharma", date(1988, 3, 14), "MALE"),
    ("Diya Patel", date(1995, 7, 2), "FEMALE"),
    ("Kabir Singh", date(1979, 11, 23), "MALE"),
    ("Meera Krishnan", date(2016, 5, 9), "FEMALE"),
    ("Ishaan Gupta", date(2001, 1, 30), "MALE"),
    ("Saanvi Joshi", date(1992, 9, 18), "FEMALE"),
    ("Rahul Verma", date(1967, 4, 5), "MALE"),
    ("Ananya Das", date(1985, 12, 11), "FEMALE"),
    ("Vivaan Malhotra", date(2012, 8, 27), "MALE"),
    ("Neha Kulkarni", date(1999, 2, 16), "FEMALE"),
    ("Aditya Bose", date(1974, 6, 21), "MALE"),
    ("Riya Chatterjee", date(2004, 10, 3), "FEMALE"),
]

REASONS = {
    "Cardiology": ["Chest pain follow-up", "ECG review", "Blood pressure check"],
    "Orthopedics": ["Knee pain", "Post-fracture review", "Lower back pain"],
    "Pediatrics": ["Vaccination", "Fever and cough", "Growth check-up"],
    "Dermatology": ["Skin rash", "Acne treatment", "Mole examination"],
    "General Medicine": ["Annual health check", "Diabetes review", "Seasonal flu"],
    "ENT": ["Ear infection", "Sinusitis", "Hearing assessment"],
}

SLOT_HOURS = [
    time(9, 0),
    time(9, 30),
    time(10, 30),
    time(11, 30),
    time(14, 0),
    time(15, 0),
    time(16, 30),
]


def _status_for(day_offset: int, rng: random.Random) -> str:
    if day_offset < 0:
        return rng.choices(["COMPLETED", "NO_SHOW", "CANCELLED"], weights=[8, 1, 1])[0]
    if day_offset == 0:
        return rng.choice(["COMPLETED", "CHECKED_IN", "SCHEDULED", "SCHEDULED"])
    return rng.choices(["SCHEDULED", "CANCELLED"], weights=[9, 1])[0]


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(func.count(Doctor.id))):
        log.info("demo data skipped: database already has doctors")
        return

    rng = random.Random(42)
    doctors = [
        Doctor(
            full_name=name,
            specialty=specialty,
            email=f"{handle}@cliniccare.example",
            phone=f"+91 98450 {10010 + i * 7:05d}",
            room=room,
        )
        for i, (name, specialty, handle, room) in enumerate(DOCTORS)
    ]
    patients = [
        Patient(
            full_name=name,
            date_of_birth=born,
            gender=gender,
            phone=f"+91 99000 {20020 + i * 13:05d}",
            email=f"{name.split()[0].lower()}@mail.example",
        )
        for i, (name, born, gender) in enumerate(PATIENTS)
    ]
    db.add_all(doctors + patients)
    db.flush()

    zone = clinic_zone()
    today = clinic_today()
    # Each patient is used once per (day, slot), and each doctor gets one patient per slot,
    # so no seeded appointment overlaps another.
    for day_offset in range(-6, 8):
        day = today + timedelta(days=day_offset)
        for slot in rng.sample(SLOT_HOURS, k=3):
            pairs = zip(rng.sample(doctors, k=3), rng.sample(patients, k=3), strict=True)
            for doctor, patient in pairs:
                starts = datetime.combine(day, slot, tzinfo=zone).astimezone(UTC)
                db.add(
                    Appointment(
                        patient=patient,
                        doctor=doctor,
                        scheduled_at=starts,
                        ends_at=starts + timedelta(minutes=30),
                        duration_minutes=30,
                        reason=rng.choice(REASONS[doctor.specialty]),
                        status=_status_for(day_offset, rng),
                    )
                )
    db.commit()
    log.info("seeded %d doctors, %d patients and demo appointments", len(doctors), len(patients))
