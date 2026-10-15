import { useEffect, useState } from 'react';

import { api } from '../api.js';
import { Avatar, EmptyState } from '../components/ui.jsx';
import { formatDate } from '../format.js';

const GENDER = { FEMALE: 'Female', MALE: 'Male', OTHER: 'Other' };

export default function Patients({ refreshKey, notify, refresh, openModal }) {
  const [search, setSearch] = useState('');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    // Small debounce so typing in the search box doesn't fire a request per key.
    const timer = setTimeout(() => {
      api
        .patients({ q: search.trim(), limit: 500 })
        .then((data) => !cancelled && setRows(data))
        .catch(() => {})
        .finally(() => !cancelled && setLoading(false));
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, refreshKey]);

  const remove = async (patient) => {
    if (!window.confirm(`Delete ${patient.full_name} from the register?`)) return;
    try {
      await api.deletePatient(patient.id);
      notify(`${patient.full_name} removed`);
      refresh();
    } catch (err) {
      notify(err.message, 'critical');
    }
  };

  return (
    <>
      <header className="page-head">
        <div>
          <p className="eyebrow">Register</p>
          <h1>Patients</h1>
          <p className="muted">Everyone who has registered with the clinic.</p>
        </div>
        <button type="button" className="primary" onClick={() => openModal('patient')}>
          + Register patient
        </button>
      </header>

      <section className="panel">
        <div className="filters">
          <input
            type="search"
            className="search"
            placeholder="Search by name or phone"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search patients"
          />
          <span className="muted small">{rows.length} patients</span>
        </div>

        {rows.length === 0 && !loading ? (
          <EmptyState title={search ? 'No patient matches that search' : 'No patients yet'} />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Age</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Registered</th>
                  <th>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td data-label="Patient">
                      <span className="person">
                        <Avatar name={p.full_name} />
                        <strong>{p.full_name}</strong>
                      </span>
                    </td>
                    <td data-label="Age" className="tabular">
                      {p.age} · {GENDER[p.gender]}
                    </td>
                    <td data-label="Phone" className="tabular">
                      {p.phone}
                    </td>
                    <td data-label="Email">{p.email ?? '—'}</td>
                    <td data-label="Registered">{formatDate(p.created_at)}</td>
                    <td className="cell-actions">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="small primary"
                          onClick={() => openModal('appointment', { patientId: p.id })}
                        >
                          Book
                        </button>
                        <button
                          type="button"
                          className="small ghost danger"
                          onClick={() => remove(p)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
