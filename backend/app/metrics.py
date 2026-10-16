"""Business metrics, exposed next to the HTTP metrics on /metrics and graphed in Grafana."""

from prometheus_client import Counter

appointments_booked = Counter(
    "clinicflow_appointments_booked_total",
    "Appointments successfully booked",
    ["specialty"],
)
appointment_status_changes = Counter(
    "clinicflow_appointment_status_changes_total",
    "Appointment status transitions",
    ["status"],
)
booking_conflicts = Counter(
    "clinicflow_booking_conflicts_total",
    "Booking attempts rejected because the doctor was already booked",
)
