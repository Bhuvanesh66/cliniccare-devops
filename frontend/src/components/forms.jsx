import { useState } from 'react';

import { localISODate } from '../format.js';
import { Field } from './ui.jsx';

const SPECIALTIES = [
  'Cardiology',
  'Dermatology',
  'ENT',
  'General Medicine',
  'Gynecology',
  'Neurology',
  'Orthopedics',
  'Pediatrics',
];

function nextHalfHour() {
  const date = new Date();
  date.setMinutes(date.getMinutes() < 30 ? 30 : 60, 0, 0);
  return date.toTimeString().slice(0, 5);
}

/** Shared submit handling: disables the form while saving and shows API errors inline. */
function useSubmit(onSubmit) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const handle = async (event, build) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await onSubmit(build(new FormData(event.currentTarget)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, handle };
}

function FormActions({ busy, error, onCancel, label }) {
  return (
    <>
      {error && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">!</span> {error}
        </p>
      )}
      <footer className="modal-actions">
        <button type="button" className="ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Saving…' : label}
        </button>
      </footer>
    </>
  );
}

export function AppointmentForm({ patients, doctors, initialPatientId, onSubmit, onCancel }) {
  const { busy, error, handle } = useSubmit(onSubmit);
  const activeDoctors = doctors.filter((d) => d.is_active);

  const build = (form) => ({
    patient_id: Number(form.get('patient_id')),
    doctor_id: Number(form.get('doctor_id')),
    // Local date + time from the inputs, sent as an absolute UTC instant.
    scheduled_at: new Date(`${form.get('date')}T${form.get('time')}`).toISOString(),
    duration_minutes: Number(form.get('duration_minutes')),
    reason: form.get('reason').trim(),
    notes: form.get('notes').trim(),
  });

  return (
    <form className="form-grid" onSubmit={(event) => handle(event, build)}>
      <Field label="Patient" wide>
        <select name="patient_id" required defaultValue={initialPatientId ?? ''}>
          <option value="" disabled>
            Select a patient
          </option>
          {patients.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name} · {p.phone}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Doctor" wide>
        <select name="doctor_id" required defaultValue="">
          <option value="" disabled>
            Select a doctor
          </option>
          {activeDoctors.map((d) => (
            <option key={d.id} value={d.id}>
              {d.full_name} · {d.specialty}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Date">
        <input type="date" name="date" required defaultValue={localISODate()} />
      </Field>
      <Field label="Time">
        <input type="time" name="time" required step={900} defaultValue={nextHalfHour()} />
      </Field>
      <Field label="Duration">
        <select name="duration_minutes" defaultValue="30">
          {[15, 30, 45, 60, 90].map((m) => (
            <option key={m} value={m}>
              {m} minutes
            </option>
          ))}
        </select>
      </Field>
      <Field label="Reason for visit">
        <input name="reason" required minLength={3} maxLength={300} placeholder="e.g. Fever" />
      </Field>
      <Field label="Notes" hint="Optional, visible to clinic staff" wide>
        <textarea name="notes" rows={2} maxLength={2000} />
      </Field>
      <FormActions busy={busy} error={error} onCancel={onCancel} label="Book appointment" />
    </form>
  );
}

export function PatientForm({ onSubmit, onCancel }) {
  const { busy, error, handle } = useSubmit(onSubmit);
  const build = (form) => ({
    full_name: form.get('full_name').trim(),
    date_of_birth: form.get('date_of_birth'),
    gender: form.get('gender'),
    phone: form.get('phone').trim(),
    email: form.get('email').trim() || null,
  });

  return (
    <form className="form-grid" onSubmit={(event) => handle(event, build)}>
      <Field label="Full name" wide>
        <input name="full_name" required minLength={2} maxLength={120} autoComplete="off" />
      </Field>
      <Field label="Date of birth">
        <input type="date" name="date_of_birth" required max={localISODate()} />
      </Field>
      <Field label="Gender">
        <select name="gender" required defaultValue="">
          <option value="" disabled>
            Select
          </option>
          <option value="FEMALE">Female</option>
          <option value="MALE">Male</option>
          <option value="OTHER">Other</option>
        </select>
      </Field>
      <Field label="Phone">
        <input name="phone" type="tel" required placeholder="+91 98450 12345" />
      </Field>
      <Field label="Email" hint="Optional">
        <input name="email" type="email" maxLength={160} />
      </Field>
      <FormActions busy={busy} error={error} onCancel={onCancel} label="Register patient" />
    </form>
  );
}

export function DoctorForm({ onSubmit, onCancel }) {
  const { busy, error, handle } = useSubmit(onSubmit);
  const build = (form) => ({
    full_name: form.get('full_name').trim(),
    specialty: form.get('specialty').trim(),
    email: form.get('email').trim(),
    phone: form.get('phone').trim(),
    room: form.get('room').trim(),
  });

  return (
    <form className="form-grid" onSubmit={(event) => handle(event, build)}>
      <Field label="Full name" wide>
        <input name="full_name" required minLength={2} placeholder="Dr. " autoComplete="off" />
      </Field>
      <Field label="Specialty">
        <input name="specialty" required list="specialties" minLength={2} maxLength={80} />
        <datalist id="specialties">
          {SPECIALTIES.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </Field>
      <Field label="Room">
        <input name="room" maxLength={20} placeholder="e.g. 204" />
      </Field>
      <Field label="Email">
        <input name="email" type="email" required maxLength={160} />
      </Field>
      <Field label="Phone">
        <input name="phone" type="tel" required placeholder="+91 98450 12345" />
      </Field>
      <FormActions busy={busy} error={error} onCancel={onCancel} label="Add doctor" />
    </form>
  );
}
