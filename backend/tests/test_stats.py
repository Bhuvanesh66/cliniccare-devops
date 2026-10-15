from datetime import datetime, time

from app.clinic_time import clinic_today, clinic_zone


def test_stats_on_empty_database(client):
    stats = client.get("/api/stats").json()
    assert stats["patients"] == 0
    assert stats["appointments_today"] == 0
    assert stats["completion_rate"] == 0.0
    assert set(stats["by_status"]) == {
        "SCHEDULED",
        "CHECKED_IN",
        "COMPLETED",
        "CANCELLED",
        "NO_SHOW",
    }


def test_stats_count_today_and_doctor_load(client, book, make_doctor, make_patient):
    busy = make_doctor(full_name="Dr. Busy")
    make_doctor(full_name="Dr. Free")
    noon_today = datetime.combine(clinic_today(), time(12, 0), tzinfo=clinic_zone()).isoformat()

    first = book(doctor=busy, scheduled_at=noon_today)
    book(doctor=busy, scheduled_at=noon_today.replace("12:00", "13:00"))
    cancelled = book(scheduled_at=noon_today.replace("12:00", "14:00"))
    client.patch(f"/api/appointments/{cancelled['id']}/status", json={"status": "CANCELLED"})
    for new_status in ("CHECKED_IN", "COMPLETED"):
        client.patch(f"/api/appointments/{first['id']}/status", json={"status": new_status})

    stats = client.get("/api/stats").json()
    assert stats["appointments_today"] == 2  # the cancelled one does not count
    assert stats["by_status"]["COMPLETED"] == 1
    assert stats["by_status"]["CANCELLED"] == 1
    assert stats["completion_rate"] == 50.0  # 1 completed out of 2 closed
    load = {row["full_name"]: row["appointments_today"] for row in stats["doctor_load"]}
    assert load["Dr. Busy"] == 2
    assert load["Dr. Free"] == 0
