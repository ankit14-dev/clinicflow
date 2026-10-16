from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Appointment, Doctor, Patient
from ..schemas import StatsOut
from ..timeutil import clinic_day_bounds, clinic_today

router = APIRouter(prefix="/api", tags=["dashboard"])

STATUSES = ("SCHEDULED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW")


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status)).all()
    by_status = {s: 0 for s in STATUSES} | {s: c for s, c in rows}

    day_start, day_end = clinic_day_bounds(clinic_today())
    today = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at >= day_start,
            Appointment.scheduled_at < day_end,
            Appointment.status != "CANCELLED",
        )
    )
    upcoming = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at >= datetime.now(UTC),
            Appointment.status == "SCHEDULED",
        )
    )
    specialty_rows = db.execute(
        select(Doctor.specialty, func.count(Appointment.id))
        .join(Appointment, Appointment.doctor_id == Doctor.id)
        .group_by(Doctor.specialty)
        .order_by(func.count(Appointment.id).desc())
    ).all()

    return StatsOut(
        total=sum(by_status.values()),
        today=today or 0,
        upcoming=upcoming or 0,
        completed=by_status["COMPLETED"],
        cancelled=by_status["CANCELLED"],
        no_show=by_status["NO_SHOW"],
        by_status=by_status,
        by_specialty=[{"specialty": s, "count": c} for s, c in specialty_rows],
        doctors_active=db.scalar(select(func.count(Doctor.id)).where(Doctor.is_active.is_(True))) or 0,
        patients=db.scalar(select(func.count(Patient.id))) or 0,
    )
