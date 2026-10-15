from datetime import date, datetime, timedelta

from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..clinic_time import day_bounds_utc
from ..db import DbSession
from ..metrics import APPOINTMENT_STATUS_CHANGES, APPOINTMENTS_BOOKED
from ..models import ACTIVE_STATUSES, STATUS_TRANSITIONS, Appointment, Doctor, Patient
from ..schemas import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentStatus,
    AppointmentStatusUpdate,
    AppointmentUpdate,
)
from .common import conflict, get_or_404

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def _with_people():
    return (joinedload(Appointment.patient), joinedload(Appointment.doctor))


def _ensure_slot_free(
    db: DbSession,
    *,
    doctor_id: int,
    patient_id: int,
    starts: datetime,
    ends: datetime,
    exclude_id: int | None = None,
) -> None:
    """Reject a booking that overlaps an active appointment of the same doctor or patient.

    Two ranges overlap when each starts before the other ends, so back-to-back
    slots (10:00-10:30 then 10:30-11:00) are allowed.
    """
    overlapping = (
        select(Appointment)
        .where(
            Appointment.status.in_(ACTIVE_STATUSES),
            Appointment.scheduled_at < ends,
            Appointment.ends_at > starts,
        )
        .options(*_with_people())
    )
    if exclude_id is not None:
        overlapping = overlapping.where(Appointment.id != exclude_id)

    clash = db.scalars(overlapping.where(Appointment.doctor_id == doctor_id)).first()
    if clash:
        raise conflict(
            f"{clash.doctor.full_name} already has appointment #{clash.id} in that time slot"
        )
    clash = db.scalars(overlapping.where(Appointment.patient_id == patient_id)).first()
    if clash:
        raise conflict(
            f"{clash.patient.full_name} already has appointment #{clash.id} in that time slot"
        )


def _active_doctor(db: DbSession, doctor_id: int) -> Doctor:
    doctor = get_or_404(db, Doctor, doctor_id)
    if not doctor.is_active:
        raise conflict(f"{doctor.full_name} is not currently taking appointments")
    return doctor


def _load(db: DbSession, appointment_id: int) -> Appointment:
    appointment = db.scalar(
        select(Appointment).where(Appointment.id == appointment_id).options(*_with_people())
    )
    if appointment is None:
        get_or_404(db, Appointment, appointment_id)  # raises the standard 404
    return appointment


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    db: DbSession,
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
    doctor_id: int | None = None,
    patient_id: int | None = None,
    day: date | None = Query(default=None, description="Clinic-local date, e.g. 2026-10-15"),
    from_day: date | None = Query(default=None, description="This clinic-local date onwards"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    query = (
        select(Appointment)
        .options(*_with_people())
        .order_by(Appointment.scheduled_at)
        .limit(limit)
        .offset(offset)
    )
    if status_filter:
        query = query.where(Appointment.status == status_filter)
    if doctor_id is not None:
        query = query.where(Appointment.doctor_id == doctor_id)
    if patient_id is not None:
        query = query.where(Appointment.patient_id == patient_id)
    if day is not None:
        start, end = day_bounds_utc(day)
        query = query.where(Appointment.scheduled_at >= start, Appointment.scheduled_at < end)
    if from_day is not None:
        query = query.where(Appointment.scheduled_at >= day_bounds_utc(from_day)[0])
    return db.scalars(query).all()


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(appointment_id: int, db: DbSession):
    return _load(db, appointment_id)


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(payload: AppointmentCreate, db: DbSession):
    get_or_404(db, Patient, payload.patient_id)
    doctor = _active_doctor(db, payload.doctor_id)
    ends = payload.scheduled_at + timedelta(minutes=payload.duration_minutes)
    _ensure_slot_free(
        db,
        doctor_id=payload.doctor_id,
        patient_id=payload.patient_id,
        starts=payload.scheduled_at,
        ends=ends,
    )
    appointment = Appointment(**payload.model_dump(), ends_at=ends)
    db.add(appointment)
    db.commit()
    APPOINTMENTS_BOOKED.labels(specialty=doctor.specialty).inc()
    return _load(db, appointment.id)


@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(appointment_id: int, payload: AppointmentUpdate, db: DbSession):
    appointment = _load(db, appointment_id)
    changes = payload.model_dump(exclude_unset=True)
    reschedule = {"doctor_id", "scheduled_at", "duration_minutes"} & changes.keys()

    if reschedule:
        if appointment.status != "SCHEDULED":
            raise conflict(
                f"Only SCHEDULED appointments can be rescheduled (is {appointment.status})"
            )
        doctor_id = changes.get("doctor_id", appointment.doctor_id)
        if doctor_id != appointment.doctor_id:
            _active_doctor(db, doctor_id)
        starts = changes.get("scheduled_at", appointment.scheduled_at)
        duration = changes.get("duration_minutes", appointment.duration_minutes)
        ends = starts + timedelta(minutes=duration)
        _ensure_slot_free(
            db,
            doctor_id=doctor_id,
            patient_id=appointment.patient_id,
            starts=starts,
            ends=ends,
            exclude_id=appointment.id,
        )
        changes["ends_at"] = ends

    for field, value in changes.items():
        setattr(appointment, field, value)
    db.commit()
    return _load(db, appointment_id)


@router.patch("/{appointment_id}/status", response_model=AppointmentOut)
def change_status(appointment_id: int, payload: AppointmentStatusUpdate, db: DbSession):
    appointment = _load(db, appointment_id)
    allowed = STATUS_TRANSITIONS[appointment.status]
    if payload.status not in allowed:
        options = ", ".join(sorted(allowed)) or "none - it is final"
        raise conflict(
            f"Cannot move appointment from {appointment.status} to {payload.status} "
            f"(allowed: {options})"
        )
    appointment.status = payload.status
    db.commit()
    APPOINTMENT_STATUS_CHANGES.labels(status=payload.status).inc()
    return _load(db, appointment_id)


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: int, db: DbSession):
    appointment = get_or_404(db, Appointment, appointment_id)
    db.delete(appointment)
    db.commit()
