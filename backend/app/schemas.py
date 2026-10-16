from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .timeutil import as_utc

AppointmentStatus = Literal["SCHEDULED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW"]

Name = Field(min_length=2, max_length=120)


# ---------- doctors ----------
class DoctorCreate(BaseModel):
    full_name: str = Name
    specialty: str = Field(min_length=2, max_length=80)
    room: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=200)
    is_active: bool = True


class DoctorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    specialty: str | None = Field(default=None, min_length=2, max_length=80)
    room: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class DoctorOut(DoctorCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- patients ----------
class PatientCreate(BaseModel):
    full_name: str = Name
    phone: str = Field(min_length=6, max_length=30, pattern=r"^[0-9+\-() ]+$")
    email: str = Field(default="", max_length=200)
    date_of_birth: date | None = None

    @field_validator("date_of_birth")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, min_length=6, max_length=30, pattern=r"^[0-9+\-() ]+$")
    email: str | None = Field(default=None, max_length=200)
    date_of_birth: date | None = None


class PatientOut(PatientCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ---------- appointments ----------
class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=10, le=240)
    reason: str = Field(min_length=3, max_length=300)
    notes: str = ""

    @field_validator("scheduled_at")
    @classmethod
    def to_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


class AppointmentUpdate(BaseModel):
    doctor_id: int | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=10, le=240)
    reason: str | None = Field(default=None, min_length=3, max_length=300)
    notes: str | None = None
    status: AppointmentStatus | None = None

    @field_validator("scheduled_at")
    @classmethod
    def to_utc(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value else value


class DoctorRef(BaseModel):
    id: int
    full_name: str
    specialty: str
    model_config = ConfigDict(from_attributes=True)


class PatientRef(BaseModel):
    id: int
    full_name: str
    phone: str
    model_config = ConfigDict(from_attributes=True)


class AppointmentOut(BaseModel):
    id: int
    scheduled_at: datetime
    duration_minutes: int
    reason: str
    notes: str
    status: AppointmentStatus
    doctor: DoctorRef
    patient: PatientRef
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_validator("scheduled_at", "created_at")
    @classmethod
    def to_utc(cls, value: datetime) -> datetime:
        return as_utc(value)


# ---------- dashboard ----------
class SpecialtyCount(BaseModel):
    specialty: str
    count: int


class StatsOut(BaseModel):
    total: int
    today: int
    upcoming: int
    completed: int
    cancelled: int
    no_show: int
    by_status: dict[str, int]
    by_specialty: list[SpecialtyCount]
    doctors_active: int
    patients: int
