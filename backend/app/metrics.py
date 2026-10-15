"""Business metrics exposed on /metrics next to the HTTP metrics from the instrumentator."""

from prometheus_client import Counter

APPOINTMENTS_BOOKED = Counter(
    "cliniccare_appointments_booked_total",
    "Appointments booked, by doctor specialty.",
    ["specialty"],
)

APPOINTMENT_STATUS_CHANGES = Counter(
    "cliniccare_appointment_status_changes_total",
    "Appointment status transitions, by the new status.",
    ["status"],
)
