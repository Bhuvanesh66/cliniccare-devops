from fastapi import APIRouter, status
from sqlalchemy import func, select

from ..db import DbSession
from ..models import Appointment, Doctor
from ..schemas import DoctorCreate, DoctorOut, DoctorUpdate
from .common import conflict, get_or_404

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


def _ensure_email_free(db: DbSession, email: str, exclude_id: int | None = None) -> None:
    query = select(Doctor.id).where(func.lower(Doctor.email) == email.lower())
    if exclude_id is not None:
        query = query.where(Doctor.id != exclude_id)
    if db.scalar(query) is not None:
        raise conflict(f"A doctor with email {email} already exists")


@router.get("", response_model=list[DoctorOut])
def list_doctors(db: DbSession, specialty: str | None = None, active: bool | None = None):
    query = select(Doctor).order_by(Doctor.full_name)
    if specialty:
        query = query.where(Doctor.specialty == specialty)
    if active is not None:
        query = query.where(Doctor.is_active.is_(active))
    return db.scalars(query).all()


@router.get("/{doctor_id}", response_model=DoctorOut)
def get_doctor(doctor_id: int, db: DbSession):
    return get_or_404(db, Doctor, doctor_id)


@router.post("", response_model=DoctorOut, status_code=status.HTTP_201_CREATED)
def create_doctor(payload: DoctorCreate, db: DbSession):
    _ensure_email_free(db, payload.email)
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    db.commit()
    return doctor


@router.put("/{doctor_id}", response_model=DoctorOut)
def update_doctor(doctor_id: int, payload: DoctorUpdate, db: DbSession):
    doctor = get_or_404(db, Doctor, doctor_id)
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        _ensure_email_free(db, changes["email"], exclude_id=doctor_id)
    for field, value in changes.items():
        setattr(doctor, field, value)
    db.commit()
    return doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(doctor_id: int, db: DbSession):
    doctor = get_or_404(db, Doctor, doctor_id)
    booked = db.scalar(select(func.count(Appointment.id)).where(Appointment.doctor_id == doctor_id))
    if booked:
        raise conflict(
            f"Doctor has {booked} appointment(s) on record; deactivate the doctor instead"
        )
    db.delete(doctor)
    db.commit()
