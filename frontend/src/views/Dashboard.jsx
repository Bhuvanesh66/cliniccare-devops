import { useEffect, useState } from 'react';

import { api } from '../api.js';
import { Timeline } from '../components/appointments.jsx';
import { DoctorLoadChart, Meter, StatTile, StatusBreakdown } from '../components/charts.jsx';
import { EmptyState } from '../components/ui.jsx';
import { formatLongDate, greeting, localISODate } from '../format.js';

export default function Dashboard({ refreshKey, onStatus, openModal }) {
  const [stats, setStats] = useState(null);
  const [today, setToday] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.stats(), api.appointments({ day: localISODate() })])
      .then(([statsData, todayData]) => {
        if (cancelled) return;
        setStats(statsData);
        setToday(todayData);
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const byStatus = stats?.by_status ?? {};
  const closed = (byStatus.COMPLETED ?? 0) + (byStatus.CANCELLED ?? 0) + (byStatus.NO_SHOW ?? 0);
  const waiting = today.filter((a) => a.status === 'CHECKED_IN').length;

  return (
    <>
      <header className="page-head">
        <div>
          <p className="eyebrow">{formatLongDate(new Date())}</p>
          <h1>{greeting()}, front desk</h1>
          <p className="muted">Here is how the clinic looks today.</p>
        </div>
        <button type="button" className="primary" onClick={() => openModal('appointment')}>
          + Book appointment
        </button>
      </header>

      <section className="kpis" aria-label="Key figures">
        <StatTile
          label="Appointments today"
          value={stats?.appointments_today}
          detail={`${waiting} patient${waiting === 1 ? '' : 's'} in the waiting room`}
          loading={loading}
        />
        <StatTile
          label="Next 7 days"
          value={stats?.upcoming_week}
          detail="scheduled visits"
          loading={loading}
        />
        <StatTile
          label="Registered patients"
          value={stats?.patients}
          detail="in the patient register"
          loading={loading}
        />
        <StatTile
          label="Doctors on duty"
          value={stats?.active_doctors}
          detail="taking appointments"
          loading={loading}
        />
      </section>

      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Today’s schedule</h2>
              <p className="muted small">{today.length} appointments, in time order</p>
            </div>
            <a className="link" href="#/appointments">
              View all →
            </a>
          </div>
          {today.length === 0 && !loading ? (
            <EmptyState title="Nothing booked for today">
              Book an appointment to see it on the schedule.
            </EmptyState>
          ) : (
            <Timeline appointments={today} onStatus={onStatus} />
          )}
        </section>

        <div className="side-column">
          <section className="panel">
            <div className="panel-head">
              <h2>Appointments by status</h2>
            </div>
            <StatusBreakdown counts={byStatus} />
            {stats && (
              <Meter
                label="Completion rate"
                value={stats.completion_rate}
                detail={`${byStatus.COMPLETED ?? 0} of ${closed} closed appointments were completed`}
              />
            )}
          </section>
          <section className="panel">
            <div className="panel-head">
              <h2>Doctor load today</h2>
            </div>
            <DoctorLoadChart rows={stats?.doctor_load ?? []} />
          </section>
        </div>
      </div>
    </>
  );
}
