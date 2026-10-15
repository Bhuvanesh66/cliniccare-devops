import { useCallback, useEffect, useState } from 'react';

import { api } from './api.js';
import { AppointmentForm, DoctorForm, PatientForm } from './components/forms.jsx';
import { Modal, Toasts, useToasts } from './components/ui.jsx';
import { STATUS_BY_KEY, shortSha } from './format.js';
import Appointments from './views/Appointments.jsx';
import Dashboard from './views/Dashboard.jsx';
import Doctors from './views/Doctors.jsx';
import Patients from './views/Patients.jsx';

const UI_BUILD = import.meta.env.VITE_GIT_SHA ?? 'local';

const ICONS = {
  dashboard: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z',
  appointments: 'M4 5h16v15H4zM4 9h16M8 3v4M16 3v4',
  patients: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21v-1a7 7 0 0 1 14 0v1M17 11h5M19.5 8.5v5',
  doctors: 'M12 21s-8-4.5-8-11a5 5 0 0 1 8-4 5 5 0 0 1 8 4c0 6.5-8 11-8 11zM12 8v6M9 11h6',
};

const PAGES = [
  { key: 'dashboard', label: 'Dashboard', View: Dashboard },
  { key: 'appointments', label: 'Appointments', View: Appointments },
  { key: 'patients', label: 'Patients', View: Patients },
  { key: 'doctors', label: 'Doctors', View: Doctors },
];

function currentPage() {
  const key = window.location.hash.replace(/^#\/?/, '');
  return PAGES.find((p) => p.key === key) ?? PAGES[0];
}

function useHashPage() {
  const [page, setPage] = useState(currentPage);
  useEffect(() => {
    const onChange = () => setPage(currentPage());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return page;
}

function Icon({ path }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

const MODAL_TITLES = {
  appointment: 'Book an appointment',
  patient: 'Register a patient',
  doctor: 'Add a doctor',
};

export default function App() {
  const page = useHashPage();
  const { toasts, notify } = useToasts();
  const [refreshKey, setRefreshKey] = useState(0);
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [apiInfo, setApiInfo] = useState(null);
  const [apiDown, setApiDown] = useState(false);
  const [modal, setModal] = useState(null);

  const refresh = useCallback(() => setRefreshKey((key) => key + 1), []);

  useEffect(() => {
    Promise.all([api.doctors(), api.patients({ limit: 500 }), api.info()])
      .then(([doctorList, patientList, info]) => {
        setDoctors(doctorList);
        setPatients(patientList);
        setApiInfo(info);
        setApiDown(false);
      })
      .catch(() => setApiDown(true));
  }, [refreshKey]);

  const openModal = (kind, options = {}) => setModal({ kind, ...options });
  const closeModal = () => setModal(null);

  const changeStatus = async (appointment, status) => {
    try {
      await api.setAppointmentStatus(appointment.id, status);
      notify(`${appointment.patient.full_name}: ${STATUS_BY_KEY[status].label.toLowerCase()}`);
      refresh();
    } catch (err) {
      notify(err.message, 'critical');
    }
  };

  const deleteAppointment = async (appointment) => {
    if (!window.confirm(`Delete appointment #${appointment.id}?`)) return;
    try {
      await api.deleteAppointment(appointment.id);
      notify(`Appointment #${appointment.id} deleted`);
      refresh();
    } catch (err) {
      notify(err.message, 'critical');
    }
  };

  // Forms throw on API errors so the modal can show them; success closes the modal.
  const saveWith = (call, message) => async (payload) => {
    const saved = await call(payload);
    closeModal();
    notify(message(saved));
    refresh();
  };

  const { View } = page;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            +
          </span>
          <div>
            <strong>ClinicCare</strong>
            <small>Appointment desk</small>
          </div>
        </div>
        <nav aria-label="Main">
          {PAGES.map((p) => (
            <a
              key={p.key}
              href={`#/${p.key}`}
              aria-current={p.key === page.key ? 'page' : undefined}
            >
              <Icon path={ICONS[p.key]} />
              <span>{p.label}</span>
            </a>
          ))}
        </nav>
        <footer className="build" aria-label="Build information">
          <span className={`api-dot ${apiDown ? 'down' : 'up'}`} aria-hidden="true" />
          <span>
            API {apiDown ? 'unreachable' : shortSha(apiInfo?.git_sha)}
            <br />
            UI {shortSha(UI_BUILD)}
            {apiInfo?.environment && ` · ${apiInfo.environment}`}
          </span>
        </footer>
      </aside>

      <main className="content">
        {apiDown && (
          <div className="alert" role="alert">
            <strong>The ClinicCare API is not reachable.</strong> Check that the backend and
            PostgreSQL are running, then <button onClick={refresh}>retry</button>.
          </div>
        )}
        <View
          refreshKey={refreshKey}
          refresh={refresh}
          notify={notify}
          doctors={doctors}
          patients={patients}
          openModal={openModal}
          onStatus={changeStatus}
          onDelete={deleteAppointment}
        />
      </main>

      <Modal title={MODAL_TITLES[modal?.kind]} open={Boolean(modal)} onClose={closeModal}>
        {modal?.kind === 'appointment' && (
          <AppointmentForm
            patients={patients}
            doctors={doctors}
            initialPatientId={modal.patientId}
            onCancel={closeModal}
            onSubmit={saveWith(
              api.bookAppointment,
              (a) => `Booked ${a.patient.full_name} with ${a.doctor.full_name}`,
            )}
          />
        )}
        {modal?.kind === 'patient' && (
          <PatientForm
            onCancel={closeModal}
            onSubmit={saveWith(api.createPatient, (p) => `${p.full_name} registered`)}
          />
        )}
        {modal?.kind === 'doctor' && (
          <DoctorForm
            onCancel={closeModal}
            onSubmit={saveWith(api.createDoctor, (d) => `${d.full_name} added`)}
          />
        )}
      </Modal>

      <Toasts toasts={toasts} />
    </div>
  );
}
