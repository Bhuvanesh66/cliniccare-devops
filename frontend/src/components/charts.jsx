import { useRef, useState } from 'react';

import { STATUSES } from '../format.js';

/** Hover/focus tooltip positioned inside a chart container. */
function useTooltip() {
  const containerRef = useRef(null);
  const [tip, setTip] = useState(null);

  const place = (x, y, content) => setTip({ x, y, content });
  const bind = (content) => ({
    onMouseMove: (event) => {
      const box = containerRef.current.getBoundingClientRect();
      place(event.clientX - box.left, event.clientY - box.top, content);
    },
    onMouseLeave: () => setTip(null),
    onFocus: (event) => {
      const box = containerRef.current.getBoundingClientRect();
      const target = event.currentTarget.getBoundingClientRect();
      place(target.left - box.left + target.width / 2, target.top - box.top, content);
    },
    onBlur: () => setTip(null),
  });

  const tooltip = tip && (
    <div className="viz-tooltip" style={{ left: tip.x, top: tip.y }}>
      {tip.content}
    </div>
  );
  return { containerRef, bind, tooltip };
}

export function StatTile({ label, value, detail, loading }) {
  return (
    <section className="stat-tile">
      <h3>{label}</h3>
      <p className="stat-value">{loading ? <span className="skeleton" /> : value}</p>
      {detail && <p className="stat-detail">{detail}</p>}
    </section>
  );
}

/** Single ratio against 100%: a meter, not a two-slice pie. */
export function Meter({ label, value, detail }) {
  return (
    <div className="meter">
      <div className="meter-head">
        <span>{label}</span>
        <strong>{value.toFixed(1)}%</strong>
      </div>
      <div
        className="meter-track"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-label={label}
      >
        <div className="meter-fill" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      {detail && <p className="muted small">{detail}</p>}
    </div>
  );
}

/** Part-to-whole of appointment states: one stacked bar plus a labelled legend. */
export function StatusBreakdown({ counts }) {
  const { containerRef, bind, tooltip } = useTooltip();
  const total = STATUSES.reduce((sum, s) => sum + (counts[s.key] ?? 0), 0);
  const pct = (n) => (total ? Math.round((100 * n) / total) : 0);

  return (
    <div className="viz" ref={containerRef}>
      {total === 0 ? (
        <p className="muted">No appointments yet.</p>
      ) : (
        <div className="stack" role="img" aria-label="Appointments by status">
          {STATUSES.filter((s) => counts[s.key]).map((s) => (
            <div
              key={s.key}
              className="stack-segment"
              style={{ flexGrow: counts[s.key], background: s.color }}
              tabIndex={0}
              {...bind(
                <>
                  <strong>{s.label}</strong>
                  <span>
                    {counts[s.key]} appointments · {pct(counts[s.key])}%
                  </span>
                </>,
              )}
            />
          ))}
        </div>
      )}
      <ul className="legend">
        {STATUSES.map((s) => (
          <li key={s.key}>
            <span className="swatch" style={{ background: s.color }} aria-hidden="true" />
            <span className="legend-label">{s.label}</span>
            <span className="legend-value">{counts[s.key] ?? 0}</span>
          </li>
        ))}
      </ul>
      {tooltip}
    </div>
  );
}

/** Magnitude comparison across doctors: horizontal bars in one hue, with a table view. */
export function DoctorLoadChart({ rows }) {
  const { containerRef, bind, tooltip } = useTooltip();
  const [asTable, setAsTable] = useState(false);
  const max = Math.max(1, ...rows.map((r) => r.appointments_today));

  if (rows.length === 0) return <p className="muted">No active doctors.</p>;

  return (
    <div className="viz" ref={containerRef}>
      <div className="viz-toggle" role="group" aria-label="Display as">
        <button type="button" aria-pressed={!asTable} onClick={() => setAsTable(false)}>
          Chart
        </button>
        <button type="button" aria-pressed={asTable} onClick={() => setAsTable(true)}>
          Table
        </button>
      </div>
      {asTable ? (
        <table className="mini-table">
          <thead>
            <tr>
              <th>Doctor</th>
              <th>Specialty</th>
              <th className="num">Today</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.doctor_id}>
                <td>{r.full_name}</td>
                <td>{r.specialty}</td>
                <td className="num">{r.appointments_today}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <ul className="bars">
          {rows.map((r) => (
            <li
              key={r.doctor_id}
              className="bar-row"
              tabIndex={0}
              {...bind(
                <>
                  <strong>{r.full_name}</strong>
                  <span>
                    {r.specialty} · {r.appointments_today} today
                  </span>
                </>,
              )}
            >
              <span className="bar-label">{r.full_name}</span>
              <span className="bar-track">
                {r.appointments_today > 0 && (
                  <span
                    className="bar"
                    style={{ width: `${(100 * r.appointments_today) / max}%` }}
                  />
                )}
              </span>
              <span className="bar-value">{r.appointments_today}</span>
            </li>
          ))}
        </ul>
      )}
      {tooltip}
    </div>
  );
}
