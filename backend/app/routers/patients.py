from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select

from ..db import DbSession
from ..models import Appointment, Patient
from ..schemas import PatientCreate, PatientOut, PatientUpdate
from .common import conflict, get_or_404

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(
    db: DbSession,
    q: str | None = Query(default=None, description="Search by name or phone"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = select(Patient).order_by(Patient.full_name).limit(limit).offset(offset)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(Patient.full_name.ilike(pattern), Patient.phone.ilike(pattern)))
    return db.scalars(query).all()


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: DbSession):
    return get_or_404(db, Patient, patient_id)


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: DbSession):
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    return patient


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, payload: PatientUpdate, db: DbSession):
    patient = get_or_404(db, Patient, patient_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(patient_id: int, db: DbSession):
    patient = get_or_404(db, Patient, patient_id)
    booked = db.scalar(
        select(func.count(Appointment.id)).where(Appointment.patient_id == patient_id)
    )
    if booked:
        raise conflict(f"Patient has {booked} appointment(s) on record and cannot be deleted")
    db.delete(patient)
    db.commit()
