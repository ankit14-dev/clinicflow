def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_ready_checks_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_root_and_info(client):
    assert client.get("/").json()["service"] == "ClinicFlow API"
    info = client.get("/api/info").json()
    assert set(info) == {"version", "environment"}


def test_metrics_exposed(client, book):
    assert book().status_code == 201
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert 'clinicflow_appointments_booked_total{specialty="Cardiology"}' in body
