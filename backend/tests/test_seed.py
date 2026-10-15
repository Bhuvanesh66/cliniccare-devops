from itertools import combinations

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import ACTIVE_STATUSES, Appointment, Doctor
from app.seed import seed_demo_data


def test_seed_is_idempotent_and_never_double_books(client):
    with SessionLocal() as db:
        seed_demo_data(db)
        seed_demo_data(db)  # second run must be a no-op
        assert db.scalar(select(func.count(Doctor.id))) == 6
        appointments = db.scalars(
            select(Appointment).where(Appointment.status.in_(ACTIVE_STATUSES))
        ).all()

    for a, b in combinations(appointments, 2):
        overlaps = a.scheduled_at < b.ends_at and b.scheduled_at < a.ends_at
        if overlaps:
            assert a.doctor_id != b.doctor_id
            assert a.patient_id != b.patient_id

    stats = client.get("/api/stats").json()
    assert stats["patients"] == 12
    assert stats["appointments_today"] > 0
