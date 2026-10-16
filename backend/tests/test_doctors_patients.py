def test_create_list_and_get_doctor(client, doctor):
    assert doctor["id"] > 0 and doctor["is_active"] is True
    assert [d["full_name"] for d in client.get("/api/doctors").json()] == ["Dr. Test House"]
    assert client.get(f"/api/doctors/{doctor['id']}").json()["specialty"] == "Cardiology"


def test_filter_active_doctors(client, doctor):
    client.put(f"/api/doctors/{doctor['id']}", json={"is_active": False})
    assert client.get("/api/doctors?active=true").json() == []
    assert len(client.get("/api/doctors?active=false").json()) == 1


def test_update_doctor_keeps_other_fields(client, doctor):
    updated = client.put(f"/api/doctors/{doctor['id']}", json={"room": "305"}).json()
    assert updated["room"] == "305"
    assert updated["full_name"] == "Dr. Test House"


def test_delete_doctor_without_appointments(client, doctor):
    assert client.delete(f"/api/doctors/{doctor['id']}").status_code == 204
    assert client.get(f"/api/doctors/{doctor['id']}").status_code == 404


def test_cannot_delete_doctor_or_patient_with_history(client, book, doctor, patient):
    book()
    assert client.delete(f"/api/doctors/{doctor['id']}").status_code == 409
    assert client.delete(f"/api/patients/{patient['id']}").status_code == 409


def test_patient_crud_and_search(client, patient):
    client.post("/api/patients", json={"full_name": "Rahul Sharma", "phone": "9123456780"})
    assert len(client.get("/api/patients").json()) == 2
    assert [p["full_name"] for p in client.get("/api/patients?q=asha").json()] == ["Asha Verma"]
    assert [p["full_name"] for p in client.get("/api/patients?q=91234").json()] == ["Rahul Sharma"]

    updated = client.put(f"/api/patients/{patient['id']}", json={"email": "asha@example.com"}).json()
    assert updated["email"] == "asha@example.com" and updated["phone"] == "+91 98765 43210"

    assert client.delete(f"/api/patients/{patient['id']}").status_code == 204
    assert client.get(f"/api/patients/{patient['id']}").status_code == 404


def test_validation_errors(client):
    assert client.post("/api/doctors", json={"full_name": "X", "specialty": "Cardiology"}).status_code == 422
    assert client.post("/api/patients", json={"full_name": "Valid Name", "phone": "not-a-phone"}).status_code == 422
    future_dob = {"full_name": "Valid Name", "phone": "9876543210", "date_of_birth": "2999-01-01"}
    assert client.post("/api/patients", json=future_dob).status_code == 422


def test_not_found(client):
    for resource in ("doctors", "patients", "appointments"):
        assert client.get(f"/api/{resource}/99999").status_code == 404
        assert client.delete(f"/api/{resource}/99999").status_code == 404
