def test_health_is_up(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_checks_migrated_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_root_and_info_identify_the_service(client):
    assert client.get("/").json()["service"] == "ClinicCare API"
    info = client.get("/api/info").json()
    assert info["service"] == "ClinicCare API"
    assert "git_sha" in info


def test_metrics_expose_http_and_business_counters(client, book):
    book()
    client.get("/api/doctors")
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert 'cliniccare_appointments_booked_total{specialty="Cardiology"}' in body


def test_openapi_lists_all_resources(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/api/doctors", "/api/patients", "/api/appointments", "/api/stats"):
        assert path in paths
