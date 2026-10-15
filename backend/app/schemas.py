from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, computed_field

PHONE_PATTERN = r"^\+?[0-9][0-9 \-]{6,18}$"
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

AppointmentStatus = Literal["SCHEDULED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW"]
Gender = Literal["FEMALE", "MALE", "OTHER"]


def as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC and normalise aware ones to UTC.

    Everything is stored in UTC; the browser converts to local time for display.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(as_utc)]


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("date of birth cannot be in the future")
    return value


BirthDate = Annotated[date, AfterValidator(_not_in_future)]


# ---------------------------------------------------------------- doctors


class DoctorCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    specialty: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=160, pattern=EMAIL_PATTERN)
    phone: str = Field(pattern=PHONE_PATTERN)
    room: str = Field(default="", max_length=20)
    is_active: bool = True


class DoctorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    specialty: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(default=None, max_length=160, pattern=EMAIL_PATTERN)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    room: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class DoctorOut(DoctorCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: UTCDateTime


# ---------------------------------------------------------------- patients


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    date_of_birth: BirthDate
    gender: Gender
    phone: str = Field(pattern=PHONE_PATTERN)
    email: str | None = Field(default=None, max_length=160, pattern=EMAIL_PATTERN)


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    date_of_birth: BirthDate | None = None
    gender: Gender | None = None
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    email: str | None = Field(default=None, max_length=160, pattern=EMAIL_PATTERN)


class PatientOut(PatientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: UTCDateTime

    @computed_field
    @property
    def age(self) -> int:
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


# ---------------------------------------------------------------- appointments


class AppointmentCreate(BaseModel):
    patient_id: int = Field(gt=0)
    doctor_id: int = Field(gt=0)
    scheduled_at: UTCDateTime
    duration_minutes: int = Field(default=30, ge=10, le=240)
    reason: str = Field(min_length=3, max_length=300)
    notes: str = Field(default="", max_length=2000)


class AppointmentUpdate(BaseModel):
    doctor_id: int | None = Field(default=None, gt=0)
    scheduled_at: UTCDateTime | None = None
    duration_minutes: int | None = Field(default=None, ge=10, le=240)
    reason: str | None = Field(default=None, min_length=3, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class PatientRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    phone: str


class DoctorRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    specialty: str


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: UTCDateTime
    ends_at: UTCDateTime
    duration_minutes: int
    reason: str
    notes: str
    status: AppointmentStatus
    created_at: UTCDateTime
    updated_at: UTCDateTime
    patient: PatientRef
    doctor: DoctorRef


# ---------------------------------------------------------------- dashboard


class DoctorLoad(BaseModel):
    doctor_id: int
    full_name: str
    specialty: str
    appointments_today: int


class StatsOut(BaseModel):
    patients: int
    active_doctors: int
    appointments_today: int
    upcoming_week: int
    by_status: dict[str, int]
    completion_rate: float
    doctor_load: list[DoctorLoad]
