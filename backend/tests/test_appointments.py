def test_book_appointment(client, book, make_doctor, make_patient):
    doctor = make_doctor(full_name="Dr. Priya Nair", specialty="Pediatrics")
    patient = make_patient(full_name="Meera Krishnan")
    appointment = book(doctor=doctor, patient=patient, duration_minutes=45)

    assert appointment["status"] == "SCHEDULED"
    # 10:00 IST is 04:30 UTC; everything is returned in UTC.
    assert appointment["scheduled_at"] == "2030-01-15T04:30:00Z"
    assert appointment["ends_at"] == "2030-01-15T05:15:00Z"
    assert appointment["doctor"]["full_name"] == "Dr. Priya Nair"
    assert appointment["patient"]["full_name"] == "Meera Krishnan"


def test_booking_unknown_patient_returns_404(book, make_doctor):
    book(patient={"id": 4242}, expect=404)


def test_inactive_doctor_cannot_be_booked(book, make_doctor):
    book(doctor=make_doctor(is_active=False), expect=409)


def test_doctor_double_booking_is_rejected(book, make_doctor):
    doctor = make_doctor()
    book(doctor=doctor)
    clash = book(doctor=doctor, scheduled_at="2030-01-15T10:15:00+05:30", expect=409)
    assert "already has appointment" in clash["detail"]


def test_patient_double_booking_is_rejected(book, make_patient):
    patient = make_patient()
    book(patient=patient)
    book(patient=patient, expect=409)  # same slot, different doctor


def test_back_to_back_slots_are_allowed(book, make_doctor):
    doctor = make_doctor()
    book(doctor=doctor)
    book(doctor=doctor, scheduled_at="2030-01-15T10:30:00+05:30")


def test_cancelled_slot_can_be_rebooked(client, book, make_doctor):
    doctor = make_doctor()
    first = book(doctor=doctor)
    client.patch(f"/api/appointments/{first['id']}/status", json={"status": "CANCELLED"})
    book(doctor=doctor)


def test_status_workflow(client, book):
    appointment = book()
    url = f"/api/appointments/{appointment['id']}/status"

    assert client.patch(url, json={"status": "CHECKED_IN"}).json()["status"] == "CHECKED_IN"
    assert client.patch(url, json={"status": "COMPLETED"}).json()["status"] == "COMPLETED"

    reopened = client.patch(url, json={"status": "SCHEDULED"})
    assert reopened.status_code == 409
    assert "it is final" in reopened.json()["detail"]


def test_unknown_status_fails_validation(client, book):
    appointment = book()
    response = client.patch(
        f"/api/appointments/{appointment['id']}/status", json={"status": "TELEPORTED"}
    )
    assert response.status_code == 422


def test_reschedule_appointment(client, book):
    appointment = book()
    response = client.put(
        f"/api/appointments/{appointment['id']}",
        json={"scheduled_at": "2030-01-16T15:00:00+05:30", "reason": "Follow-up visit"},
    )
    assert response.status_code == 200
    assert response.json()["scheduled_at"] == "2030-01-16T09:30:00Z"
    assert response.json()["ends_at"] == "2030-01-16T10:00:00Z"
    assert response.json()["reason"] == "Follow-up visit"


def test_completed_appointment_cannot_be_rescheduled(client, book):
    appointment = book()
    url = f"/api/appointments/{appointment['id']}"
    client.patch(f"{url}/status", json={"status": "CHECKED_IN"})
    response = client.put(url, json={"scheduled_at": "2030-02-01T10:00:00+05:30"})
    assert response.status_code == 409


def test_list_filters(client, book, make_doctor):
    doctor = make_doctor()
    book(doctor=doctor)
    book(doctor=doctor, scheduled_at="2030-01-16T10:00:00+05:30")
    other = book()
    client.patch(f"/api/appointments/{other['id']}/status", json={"status": "CANCELLED"})

    assert len(client.get("/api/appointments", params={"doctor_id": doctor["id"]}).json()) == 2
    assert len(client.get("/api/appointments", params={"status": "CANCELLED"}).json()) == 1
    assert len(client.get("/api/appointments", params={"day": "2030-01-16"}).json()) == 1
    assert len(client.get("/api/appointments", params={"from_day": "2030-01-16"}).json()) == 1


def test_delete_appointment(client, book):
    appointment = book()
    assert client.delete(f"/api/appointments/{appointment['id']}").status_code == 204
    assert client.get(f"/api/appointments/{appointment['id']}").status_code == 404
