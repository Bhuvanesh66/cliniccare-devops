from datetime import date, timedelta


def test_create_patient_returns_age(client, make_patient):
    born = date.today().replace(year=date.today().year - 30) - timedelta(days=1)
    patient = make_patient(full_name="Diya Patel", date_of_birth=born.isoformat())
    assert patient["age"] == 30
    assert client.get(f"/api/patients/{patient['id']}").json()["full_name"] == "Diya Patel"


def test_birth_date_in_future_is_rejected(client):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = client.post(
        "/api/patients",
        json={
            "full_name": "Future Person",
            "date_of_birth": tomorrow,
            "gender": "MALE",
            "phone": "+91 99000 12345",
        },
    )
    assert response.status_code == 422


def test_search_by_name_or_phone(client, make_patient):
    make_patient(full_name="Kabir Singh", phone="+91 90000 11111")
    make_patient(full_name="Meera Krishnan", phone="+91 90000 22222")

    by_name = client.get("/api/patients", params={"q": "kabir"}).json()
    assert [p["full_name"] for p in by_name] == ["Kabir Singh"]
    by_phone = client.get("/api/patients", params={"q": "22222"}).json()
    assert [p["full_name"] for p in by_phone] == ["Meera Krishnan"]


def test_update_and_delete_patient(client, make_patient):
    patient = make_patient()
    updated = client.put(f"/api/patients/{patient['id']}", json={"phone": "+91 91234 56789"})
    assert updated.status_code == 200
    assert updated.json()["phone"] == "+91 91234 56789"

    assert client.delete(f"/api/patients/{patient['id']}").status_code == 204
    assert client.get(f"/api/patients/{patient['id']}").status_code == 404


def test_missing_patient_returns_404(client):
    response = client.get("/api/patients/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Patient 9999 not found"
