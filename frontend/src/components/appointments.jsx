import { NEXT_ACTIONS, formatDate, formatTime } from '../format.js';
import { StatusBadge } from './ui.jsx';

export function AppointmentActions({ appointment, onStatus, onDelete }) {
  const actions = NEXT_ACTIONS[appointment.status] ?? [];
  return (
    <div className="row-actions">
      {actions.map((action) => (
        <button
          key={action.to}
          type="button"
          className={action.primary ? 'small primary' : 'small ghost'}
          onClick={() => onStatus(appointment, action.to)}
        >
          {action.label}
        </button>
      ))}
      {onDelete && actions.length === 0 && (
        <button type="button" className="small ghost danger" onClick={() => onDelete(appointment)}>
          Delete
        </button>
      )}
    </div>
  );
}

export function AppointmentTable({ appointments, onStatus, onDelete }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>When</th>
            <th>Patient</th>
            <th>Doctor</th>
            <th>Reason</th>
            <th>Status</th>
            <th>
              <span className="visually-hidden">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((a) => (
            <tr key={a.id}>
              <td data-label="When">
                <strong>{formatDate(a.scheduled_at)}</strong>
                <span className="cell-sub tabular">
                  {formatTime(a.scheduled_at)} – {formatTime(a.ends_at)}
                </span>
              </td>
              <td data-label="Patient">
                <strong>{a.patient.full_name}</strong>
                <span className="cell-sub">{a.patient.phone}</span>
              </td>
              <td data-label="Doctor">
                <strong>{a.doctor.full_name}</strong>
                <span className="cell-sub">{a.doctor.specialty}</span>
              </td>
              <td data-label="Reason">{a.reason}</td>
              <td data-label="Status">
                <StatusBadge status={a.status} />
              </td>
              <td className="cell-actions">
                <AppointmentActions appointment={a} onStatus={onStatus} onDelete={onDelete} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Timeline({ appointments, onStatus }) {
  return (
    <ol className="timeline">
      {appointments.map((a) => (
        <li key={a.id} className={`timeline-item status-${a.status.toLowerCase()}`}>
          <span className="timeline-time tabular">{formatTime(a.scheduled_at)}</span>
          <div className="timeline-main">
            <strong>{a.patient.full_name}</strong>
            <span className="cell-sub">
              {a.doctor.full_name} · {a.reason}
            </span>
          </div>
          <StatusBadge status={a.status} />
          <AppointmentActions appointment={a} onStatus={onStatus} />
        </li>
      ))}
    </ol>
  );
}
