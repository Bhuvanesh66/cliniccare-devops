import { api } from '../api.js';
import { Avatar, EmptyState } from '../components/ui.jsx';

export default function Doctors({ doctors, notify, refresh, openModal }) {
  const toggle = async (doctor) => {
    try {
      await api.updateDoctor(doctor.id, { is_active: !doctor.is_active });
      notify(`${doctor.full_name} is ${doctor.is_active ? 'now off duty' : 'back on duty'}`);
      refresh();
    } catch (err) {
      notify(err.message, 'critical');
    }
  };

  return (
    <>
      <header className="page-head">
        <div>
          <p className="eyebrow">Staff</p>
          <h1>Doctors</h1>
          <p className="muted">Who is taking appointments, and where to find them.</p>
        </div>
        <button type="button" className="primary" onClick={() => openModal('doctor')}>
          + Add doctor
        </button>
      </header>

      {doctors.length === 0 ? (
        <section className="panel">
          <EmptyState title="No doctors yet">Add the first doctor to start booking.</EmptyState>
        </section>
      ) : (
        <section className="doctor-grid">
          {doctors.map((d) => (
            <article key={d.id} className={`panel doctor-card${d.is_active ? '' : ' inactive'}`}>
              <div className="person">
                <Avatar name={d.full_name} tone="brand" />
                <div>
                  <h2>{d.full_name}</h2>
                  <p className="muted small">{d.specialty}</p>
                </div>
              </div>
              <dl className="facts">
                <div>
                  <dt>Room</dt>
                  <dd>{d.room || '—'}</dd>
                </div>
                <div>
                  <dt>Phone</dt>
                  <dd className="tabular">{d.phone}</dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>{d.email}</dd>
                </div>
              </dl>
              <footer className="doctor-foot">
                <span className={`duty ${d.is_active ? 'on' : 'off'}`}>
                  <span aria-hidden="true">{d.is_active ? '●' : '○'}</span>
                  {d.is_active ? 'On duty' : 'Off duty'}
                </span>
                <button type="button" className="small ghost" onClick={() => toggle(d)}>
                  {d.is_active ? 'Mark off duty' : 'Mark on duty'}
                </button>
              </footer>
            </article>
          ))}
        </section>
      )}
    </>
  );
}
