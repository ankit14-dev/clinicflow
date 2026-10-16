from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Appointment, Patient
from ..schemas import AppointmentOut, PatientCreate, PatientOut, PatientUpdate

router = APIRouter(prefix="/api/patients", tags=["patients"])


def get_patient_or_404(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("", response_model=list[PatientOut])
def list_patients(q: str | None = Query(default=None, max_length=100), db: Session = Depends(get_db)):
    stmt = select(Patient).order_by(Patient.full_name)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Patient.full_name.ilike(like), Patient.phone.ilike(like), Patient.email.ilike(like)))
    return list(db.scalars(stmt))


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    return get_patient_or_404(db, patient_id)


@router.get("/{patient_id}/appointments", response_model=list[AppointmentOut])
def patient_history(patient_id: int, db: Session = Depends(get_db)):
    get_patient_or_404(db, patient_id)
    stmt = select(Appointment).where(Appointment.patient_id == patient_id).order_by(Appointment.scheduled_at.desc())
    return list(db.scalars(stmt))


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = get_patient_or_404(db, patient_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, key, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient_or_404(db, patient_id)
    if db.scalar(select(exists().where(Appointment.patient_id == patient_id))):
        raise HTTPException(status_code=409, detail="Patient has appointment history and cannot be deleted")
    db.delete(patient)
    db.commit()
