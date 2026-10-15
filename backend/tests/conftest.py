"""Shared fixtures.

The tests never touch PostgreSQL: DATABASE_URL is pointed at a throw-away
SQLite file *before* the app is imported, and the schema is built by running
the real Alembic migrations, so the migrations are tested too.
"""

import os
import shutil
import tempfile
from pathlib import Path

_TEST_DIR = Path(tempfile.mkdtemp(prefix="cliniccare-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["SEED_DEMO_DATA"] = "false"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.migrate import alembic_config  # noqa: E402

# A fixed future slot keeps booking tests independent of the current date.
FUTURE_SLOT = "2030-01-15T10:00:00+05:30"


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    command.upgrade(alembic_config(), "head")
    yield
    engine.dispose()
    shutil.rmtree(_TEST_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_doctor(client):
    counter = iter(range(1, 1000))

    def _make(**overrides):
        n = next(counter)
        payload = {
            "full_name": f"Dr. Test {n}",
            "specialty": "Cardiology",
            "email": f"doctor{n}@cliniccare.test",
            "phone": "+91 98450 00000",
            "room": "101",
        } | overrides
        response = client.post("/api/doctors", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def make_patient(client):
    counter = iter(range(1, 1000))

    def _make(**overrides):
        n = next(counter)
        payload = {
            "full_name": f"Patient {n}",
            "date_of_birth": "1990-05-20",
            "gender": "FEMALE",
            "phone": "+91 99000 00000",
        } | overrides
        response = client.post("/api/patients", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def book(client, make_doctor, make_patient):
    """Book an appointment, creating the doctor/patient when not given."""

    def _book(doctor=None, patient=None, expect=201, **overrides):
        doctor = doctor or make_doctor()
        patient = patient or make_patient()
        payload = {
            "doctor_id": doctor["id"],
            "patient_id": patient["id"],
            "scheduled_at": FUTURE_SLOT,
            "duration_minutes": 30,
            "reason": "Routine check-up",
        } | overrides
        response = client.post("/api/appointments", json=payload)
        assert response.status_code == expect, response.text
        return response.json()

    return _book
