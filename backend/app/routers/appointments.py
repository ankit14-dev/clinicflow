from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import metrics
from ..db import get_db
from ..models import Appointment, Doctor
from ..schemas import AppointmentCreate, AppointmentOut, AppointmentStatus, AppointmentUpdate
from ..timeutil import as_utc, clinic_day_bounds
from .doctors import get_doctor_or_404
from .patients import get_patient_or_404

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

# statuses that occupy the doctor's time slot
ACTIVE_STATUSES = ("SCHEDULED", "CHECKED_IN")
MAX_DURATION = timedelta(minutes=240)  # same bound as the schema; limits the overlap search window

# the front desk workflow: which status can follow which
TRANSITIONS: dict[str, set[str]] = {
    "SCHEDULED": {"CHECKED_IN", "CANCELLED", "NO_SHOW"},
    "CHECKED_IN": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "NO_SHOW": set(),
}


def get_appointment_or_404(db: Session, appointment_id: int) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def require_bookable_doctor(db: Session, doctor_id: int) -> Doctor:
    doctor = get_doctor_or_404(db, doctor_id)
    if not doctor.is_active:
        raise HTTPException(status_code=409, detail="Doctor is not accepting appointments")
    return doctor


def require_future(start: datetime) -> None:
    if start <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Appointment time must be in the future")


def ensure_slot_free(db: Session, doctor_id: int, start: datetime, minutes: int, exclude_id: int | None = None) -> None:
    """409 if the doctor already has an active appointment overlapping [start, start + minutes)."""
    end = start + timedelta(minutes=minutes)
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.scheduled_at < end,
        Appointment.scheduled_at > start - MAX_DURATION,
    )
    if exclude_id is not None:
        stmt = stmt.where(Appointment.id != exclude_id)
    for other in db.scalars(stmt).unique():
        if as_utc(other.scheduled_at) + timedelta(minutes=other.duration_minutes) > start:
            metrics.booking_conflicts.inc()
            raise HTTPException(
                status_code=409,
                detail=f"Doctor already has appointment #{other.id} at {as_utc(other.scheduled_at).isoformat()}",
            )


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
    doctor_id: int | None = None,
    patient_id: int | None = None,
    on: date | None = Query(default=None, description="Calendar day at the clinic, YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    stmt = select(Appointment).order_by(Appointment.scheduled_at)
    if status_filter:
        stmt = stmt.where(Appointment.status == status_filter)
    if doctor_id:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if patient_id:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if on:
        start, end = clinic_day_bounds(on)
        stmt = stmt.where(Appointment.scheduled_at >= start, Appointment.scheduled_at < end)
    return list(db.scalars(stmt).unique())


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    return get_appointment_or_404(db, appointment_id)


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    get_patient_or_404(db, payload.patient_id)
    doctor = require_bookable_doctor(db, payload.doctor_id)
    require_future(payload.scheduled_at)
    ensure_slot_free(db, doctor.id, payload.scheduled_at, payload.duration_minutes)

    appointment = Appointment(**payload.model_dump(), status="SCHEDULED")
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    metrics.appointments_booked.labels(specialty=doctor.specialty).inc()
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, payload: AppointmentUpdate, db: Session = Depends(get_db)):
    appointment = get_appointment_or_404(db, appointment_id)
    changes = payload.model_dump(exclude_unset=True)

    new_status = changes.pop("status", None)
    if new_status and new_status != appointment.status:
        if new_status not in TRANSITIONS[appointment.status]:
            raise HTTPException(status_code=409, detail=f"Cannot change status {appointment.status} -> {new_status}")
    else:
        new_status = None

    rescheduling = any(
        key in changes and changes[key] != getattr(appointment, key)
        for key in ("doctor_id", "scheduled_at", "duration_minutes")
    )
    if rescheduling:
        if appointment.status != "SCHEDULED" or new_status:
            raise HTTPException(status_code=409, detail="Only SCHEDULED appointments can be rescheduled")
        doctor_id = changes.get("doctor_id", appointment.doctor_id)
        start = changes.get("scheduled_at", as_utc(appointment.scheduled_at))
        minutes = changes.get("duration_minutes", appointment.duration_minutes)
        require_bookable_doctor(db, doctor_id)
        require_future(start)
        ensure_slot_free(db, doctor_id, start, minutes, exclude_id=appointment.id)

    for key, value in changes.items():
        setattr(appointment, key, value)
    if new_status:
        appointment.status = new_status
    db.commit()
    db.refresh(appointment)
    if new_status:
        metrics.appointment_status_changes.labels(status=new_status).inc()
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = get_appointment_or_404(db, appointment_id)
    db.delete(appointment)
    db.commit()
