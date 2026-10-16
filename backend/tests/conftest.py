"""Test setup.

Tests never touch the real database: CI points TEST_DATABASE_URL at a throwaway PostgreSQL
service container, and locally the suite falls back to a SQLite file.
"""

import os
from datetime import UTC, datetime, timedelta

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///./test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def doctor(client):
    return client.post(
        "/api/doctors", json={"full_name": "Dr. Test House", "specialty": "Cardiology", "room": "201"}
    ).json()


@pytest.fixture()
def patient(client):
    return client.post("/api/patients", json={"full_name": "Asha Verma", "phone": "+91 98765 43210"}).json()


def at(days: int = 1, hour: int = 10, minute: int = 0) -> str:
    """ISO timestamp `days` from now at hh:mm UTC — always in the future for days >= 1."""
    day = datetime.now(UTC) + timedelta(days=days)
    return day.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


@pytest.fixture()
def book(client, doctor, patient):
    def _book(when: str | None = None, **overrides):
        payload = {
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "scheduled_at": when or at(),
            "reason": "Routine check-up",
        } | overrides
        return client.post("/api/appointments", json=payload)

    return _book
