import { useEffect, useState } from 'react';

import { api } from '../api.js';
import { AppointmentTable } from '../components/appointments.jsx';
import { EmptyState } from '../components/ui.jsx';
import { STATUSES, localISODate } from '../format.js';

// Default view: today onwards. Picking a specific day replaces the range.
const DEFAULT_FILTERS = { status: '', doctor_id: '', day: '', from_day: localISODate() };

export default function Appointments({ refreshKey, doctors, onStatus, onDelete, openModal }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .appointments(filters)
      .then((data) => !cancelled && setRows(data))
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters, refreshKey]);

  const set = (key) => (event) => setFilters((f) => ({ ...f, [key]: event.target.value }));
  const setDay = (event) =>
    setFilters((f) => ({
      ...f,
      day: event.target.value,
      from_day: event.target.value ? '' : f.from_day,
    }));
  const setRange = (event) => setFilters((f) => ({ ...f, day: '', from_day: event.target.value }));
  const changed = JSON.stringify(filters) !== JSON.stringify(DEFAULT_FILTERS);

  return (
    <>
      <header className="page-head">
        <div>
          <p className="eyebrow">Front desk</p>
          <h1>Appointments</h1>
          <p className="muted">Check patients in, complete visits and manage the calendar.</p>
        </div>
        <button type="button" className="primary" onClick={() => openModal('appointment')}>
          + Book appointment
        </button>
      </header>

      <section className="panel">
        <div className="filters">
          <div className="segmented" role="group" aria-label="Filter by status">
            {[{ key: '', label: 'All' }, ...STATUSES].map((s) => (
              <button
                key={s.key || 'all'}
                type="button"
                aria-pressed={filters.status === s.key}
                onClick={() => setFilters((f) => ({ ...f, status: s.key }))}
              >
                {s.label}
              </button>
            ))}
          </div>
          <select value={filters.doctor_id} onChange={set('doctor_id')} aria-label="Doctor">
            <option value="">All doctors</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
          <select
            value={filters.day ? 'day' : filters.from_day}
            onChange={setRange}
            aria-label="Dates"
          >
            <option value={localISODate()}>Today onwards</option>
            <option value="">All dates</option>
            {filters.day && <option value="day">Selected day</option>}
          </select>
          <input type="date" value={filters.day} onChange={setDay} aria-label="Specific day" />
          {changed && (
            <button type="button" className="ghost" onClick={() => setFilters(DEFAULT_FILTERS)}>
              Reset filters
            </button>
          )}
        </div>

        {rows.length === 0 && !loading ? (
          <EmptyState title="No appointments match">
            Try another status, doctor or day — or book a new appointment.
          </EmptyState>
        ) : (
          <AppointmentTable appointments={rows} onStatus={onStatus} onDelete={onDelete} />
        )}
      </section>
    </>
  );
}
