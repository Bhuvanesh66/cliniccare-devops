def test_create_and_fetch_doctor(client, make_doctor):
    doctor = make_doctor(full_name="Dr. Ananya Rao", specialty="Cardiology")
    fetched = client.get(f"/api/doctors/{doctor['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["full_name"] == "Dr. Ananya Rao"
    assert fetched.json()["is_active"] is True


def test_duplicate_email_is_rejected(client, make_doctor):
    make_doctor(email="same@cliniccare.test")
    response = client.post(
        "/api/doctors",
        json={
            "full_name": "Dr. Copy",
            "specialty": "ENT",
            "email": "SAME@cliniccare.test",
            "phone": "+91 98450 11111",
        },
    )
    assert response.status_code == 409


def test_invalid_email_and_phone_fail_validation(client):
    response = client.post(
        "/api/doctors",
        json={"full_name": "Dr. Bad", "specialty": "ENT", "email": "not-an-email", "phone": "abc"},
    )
    assert response.status_code == 422
    fields = {error["loc"][-1] for error in response.json()["detail"]}
    assert fields == {"email", "phone"}


def test_filter_by_active_and_specialty(client, make_doctor):
    make_doctor(specialty="Cardiology")
    make_doctor(specialty="ENT")
    make_doctor(specialty="ENT", is_active=False)

    ent = client.get("/api/doctors", params={"specialty": "ENT"}).json()
    assert len(ent) == 2
    active_ent = client.get("/api/doctors", params={"specialty": "ENT", "active": True}).json()
    assert len(active_ent) == 1


def test_update_doctor(client, make_doctor):
    doctor = make_doctor()
    response = client.put(f"/api/doctors/{doctor['id']}", json={"room": "305", "is_active": False})
    assert response.status_code == 200
    assert response.json()["room"] == "305"
    assert response.json()["is_active"] is False


def test_delete_doctor_without_appointments(client, make_doctor):
    doctor = make_doctor()
    assert client.delete(f"/api/doctors/{doctor['id']}").status_code == 204
    assert client.get(f"/api/doctors/{doctor['id']}").status_code == 404


def test_doctor_with_appointments_cannot_be_deleted(client, book, make_doctor):
    doctor = make_doctor()
    book(doctor=doctor)
    response = client.delete(f"/api/doctors/{doctor['id']}")
    assert response.status_code == 409
    assert "deactivate" in response.json()["detail"]
