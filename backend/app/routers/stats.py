from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import and_, func, select

from ..clinic_time import clinic_today, day_bounds_utc
from ..db import DbSession
from ..models import Appointment, Doctor, Patient, utcnow
from ..schemas import DoctorLoad, StatsOut

router = APIRouter(prefix="/api/stats", tags=["dashboard"])

STATUSES = ("SCHEDULED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW")
CLOSED_STATUSES = ("COMPLETED", "CANCELLED", "NO_SHOW")


@router.get("", response_model=StatsOut)
def dashboard_stats(db: DbSession):
    today_start, today_end = day_bounds_utc(clinic_today())
    now = utcnow()

    patients = db.scalar(select(func.count(Patient.id))) or 0
    active_doctors = db.scalar(select(func.count(Doctor.id)).where(Doctor.is_active.is_(True))) or 0
    appointments_today = (
        db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.scheduled_at >= today_start,
                Appointment.scheduled_at < today_end,
                Appointment.status != "CANCELLED",
            )
        )
        or 0
    )
    upcoming_week = (
        db.scalar(
            select(func.count(Appointment.id)).where(
                Appointment.scheduled_at >= now,
                Appointment.scheduled_at < now + timedelta(days=7),
                Appointment.status == "SCHEDULED",
            )
        )
        or 0
    )

    status_rows = db.execute(
        select(Appointment.status, func.count()).group_by(Appointment.status)
    ).all()
    counts = dict(status_rows)
    by_status = {name: counts.get(name, 0) for name in STATUSES}
    closed = sum(by_status[name] for name in CLOSED_STATUSES)
    completion_rate = round(100 * by_status["COMPLETED"] / closed, 1) if closed else 0.0

    load_rows = db.execute(
        select(Doctor.id, Doctor.full_name, Doctor.specialty, func.count(Appointment.id))
        .outerjoin(
            Appointment,
            and_(
                Appointment.doctor_id == Doctor.id,
                Appointment.scheduled_at >= today_start,
                Appointment.scheduled_at < today_end,
                Appointment.status != "CANCELLED",
            ),
        )
        .where(Doctor.is_active.is_(True))
        .group_by(Doctor.id, Doctor.full_name, Doctor.specialty)
        .order_by(func.count(Appointment.id).desc(), Doctor.full_name)
    ).all()

    return StatsOut(
        patients=patients,
        active_doctors=active_doctors,
        appointments_today=appointments_today,
        upcoming_week=upcoming_week,
        by_status=by_status,
        completion_rate=completion_rate,
        doctor_load=[
            DoctorLoad(
                doctor_id=doctor_id,
                full_name=full_name,
                specialty=specialty,
                appointments_today=count,
            )
            for doctor_id, full_name, specialty, count in load_rows
        ],
    )
