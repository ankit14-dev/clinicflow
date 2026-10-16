from datetime import UTC, datetime, timedelta

from app.timeutil import clinic_today, clinic_tz
from tests.conftest import at


def test_book_appointment(book, doctor, patient):
    response = book(duration_minutes=45)
    assert response.status_code == 201
    appt = response.json()
    assert appt["status"] == "SCHEDULED"
    assert appt["duration_minutes"] == 45
    assert appt["doctor"] == {"id": doctor["id"], "full_name": "Dr. Test House", "specialty": "Cardiology"}
    assert appt["patient"]["full_name"] == patient["full_name"]


def test_booking_unknown_patient_or_doctor(book):
    assert book(patient_id=99999).status_code == 404
    assert book(doctor_id=99999).status_code == 404


def test_cannot_book_in_the_past(book):
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    response = book(past)
    assert response.status_code == 422
    assert "future" in response.json()["detail"]


def test_cannot_book_inactive_doctor(client, book, doctor):
    client.put(f"/api/doctors/{doctor['id']}", json={"is_active": False})
    assert book().status_code == 409


def test_double_booking_is_rejected(book):
    assert book(at(hour=10, minute=0), duration_minutes=30).status_code == 201
    clash = book(at(hour=10, minute=15))
    assert clash.status_code == 409
    assert "already has appointment" in clash.json()["detail"]
    # back-to-back is fine: 10:30 starts exactly when the first one ends
    assert book(at(hour=10, minute=30)).status_code == 201


def test_cancelled_slot_can_be_rebooked(client, book):
    first = book(at(hour=11)).json()
    client.put(f"/api/appointments/{first['id']}", json={"status": "CANCELLED"})
    assert book(at(hour=11)).status_code == 201


def test_status_workflow(client, book):
    appt = book().json()
    url = f"/api/appointments/{appt['id']}"
    assert client.put(url, json={"status": "CHECKED_IN"}).json()["status"] == "CHECKED_IN"
    assert client.put(url, json={"status": "COMPLETED", "notes": "BP normal"}).json()["notes"] == "BP normal"
    # COMPLETED is terminal
    assert client.put(url, json={"status": "SCHEDULED"}).status_code == 409


def test_invalid_transition(client, book):
    appt = book().json()
    assert client.put(f"/api/appointments/{appt['id']}", json={"status": "COMPLETED"}).status_code == 409


def test_reschedule_checks_conflicts(client, book):
    a = book(at(hour=9)).json()
    b = book(at(hour=14)).json()
    assert client.put(f"/api/appointments/{b['id']}", json={"scheduled_at": at(hour=9, minute=10)}).status_code == 409
    moved = client.put(f"/api/appointments/{b['id']}", json={"scheduled_at": at(hour=16)})
    assert moved.status_code == 200
    # extending an appointment into its own old slot must not conflict with itself
    assert client.put(f"/api/appointments/{a['id']}", json={"duration_minutes": 60}).status_code == 200


def test_cannot_reschedule_after_check_in(client, book):
    appt = book().json()
    url = f"/api/appointments/{appt['id']}"
    client.put(url, json={"status": "CHECKED_IN"})
    assert client.put(url, json={"scheduled_at": at(days=2)}).status_code == 409


def test_list_filters_and_ordering(client, book, doctor, patient):
    late = book(at(days=3, hour=12)).json()
    early = book(at(days=2, hour=9)).json()
    client.put(f"/api/appointments/{late['id']}", json={"status": "CANCELLED"})

    assert [a["id"] for a in client.get("/api/appointments").json()] == [early["id"], late["id"]]
    assert [a["id"] for a in client.get("/api/appointments?status=CANCELLED").json()] == [late["id"]]
    assert len(client.get(f"/api/appointments?doctor_id={doctor['id']}").json()) == 2
    assert len(client.get(f"/api/patients/{patient['id']}/appointments").json()) == 2
    assert client.get("/api/appointments?status=BOGUS").status_code == 422


def test_delete_appointment(client, book):
    appt = book().json()
    assert client.delete(f"/api/appointments/{appt['id']}").status_code == 204
    assert client.get(f"/api/appointments/{appt['id']}").status_code == 404


def test_stats(client, book):
    soon = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
    a = book(soon).json()
    b = book(at(days=2)).json()
    book(at(days=3))
    client.put(f"/api/appointments/{b['id']}", json={"status": "CANCELLED"})

    stats = client.get("/api/stats").json()
    assert stats["total"] == 3
    assert stats["upcoming"] == 2
    assert stats["cancelled"] == 1
    assert stats["by_status"]["SCHEDULED"] == 2
    assert stats["by_specialty"] == [{"specialty": "Cardiology", "count": 3}]
    assert stats["doctors_active"] == 1 and stats["patients"] == 1
    # "today" is in the clinic's timezone; the 5-minute appointment may fall on tomorrow near midnight
    booked_day = datetime.fromisoformat(a["scheduled_at"]).astimezone(clinic_tz()).date()
    assert stats["today"] == (1 if booked_day == clinic_today() else 0)
