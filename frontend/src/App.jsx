import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './components/Dashboard.jsx';
import Appointments from './components/Appointments.jsx';
import Doctors from './components/Doctors.jsx';
import Patients from './components/Patients.jsx';
import BookingModal from './components/BookingModal.jsx';
import PatientModal from './components/PatientModal.jsx';
import DoctorModal from './components/DoctorModal.jsx';

const TITLES = {
  dashboard: ['Front desk', 'Today at the clinic'],
  appointments: ['Appointments', 'Book, check in and close out visits'],
  doctors: ['Doctors', 'Who is consulting and where'],
  patients: ['Patients', 'Registered patients and visit history'],
};

const EMPTY_STATS = { total: 0, today: 0, upcoming: 0, completed: 0, cancelled: 0, no_show: 0, by_status: {}, by_specialty: [], doctors_active: 0, patients: 0 };

export default function App() {
  const [view, setView] = useState('dashboard');
  const [data, setData] = useState({ stats: EMPTY_STATS, appointments: [], doctors: [], patients: [], info: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState(null);
  const [modal, setModal] = useState(null); // {type: 'booking'|'patient'|'doctor', ...props}

  const load = useCallback(async () => {
    try {
      const [stats, appointments, doctors, patients, info] = await Promise.all([
        api.stats(),
        api.appointments.list(),
        api.doctors.list(),
        api.patients.list(),
        api.info(),
      ]);
      setData({ stats, appointments, doctors, patients, info });
      setError('');
    } catch (e) {
      setError(e.message === 'Failed to fetch' ? 'Cannot reach the ClinicFlow API' : e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 30_000); // keep the front-desk screen fresh
    return () => clearInterval(timer);
  }, [load]);

  const notify = (message, kind = 'ok') => {
    setToast({ message, kind });
    setTimeout(() => setToast(null), 3500);
  };

  // run an API call, then refresh everything and show the outcome
  const act = async (fn, success) => {
    try {
      await fn();
      if (success) notify(success);
      await load();
      return true;
    } catch (e) {
      notify(e.message, 'error');
      return false;
    }
  };

  const openBooking = (preset = {}) => setModal({ type: 'booking', preset });
  const [title, subtitle] = TITLES[view];
  const shared = { ...data, act, openBooking };

  return (
    <div className="app">
      <Sidebar view={view} onNavigate={setView} info={data.info} stats={data.stats} />

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{title}</h1>
            <p className="muted">{subtitle}</p>
          </div>
          <div className="topbar-actions">
            {view === 'patients' && (
              <button className="btn" onClick={() => setModal({ type: 'patient' })}>+ Patient</button>
            )}
            {view === 'doctors' && (
              <button className="btn" onClick={() => setModal({ type: 'doctor' })}>+ Doctor</button>
            )}
            <button className="btn btn-primary" onClick={() => openBooking()}>+ Book appointment</button>
          </div>
        </header>

        {error && (
          <div className="banner banner-error" role="alert">
            <strong>Backend unavailable.</strong> {error}. Retrying every 30 seconds.
            <button className="btn btn-small" onClick={load}>Retry now</button>
          </div>
        )}

        {loading ? (
          <div className="skeleton-grid" aria-busy="true">
            {Array.from({ length: 4 }, (_, i) => <div key={i} className="skeleton" />)}
          </div>
        ) : (
          <>
            {view === 'dashboard' && <Dashboard {...shared} onNavigate={setView} />}
            {view === 'appointments' && <Appointments {...shared} />}
            {view === 'doctors' && <Doctors {...shared} onAdd={() => setModal({ type: 'doctor' })} />}
            {view === 'patients' && <Patients {...shared} onAdd={() => setModal({ type: 'patient' })} />}
          </>
        )}
      </main>

      {modal?.type === 'booking' && (
        <BookingModal
          doctors={data.doctors}
          patients={data.patients}
          preset={modal.preset}
          act={act}
          onClose={() => setModal(null)}
        />
      )}
      {modal?.type === 'patient' && <PatientModal act={act} onClose={() => setModal(null)} />}
      {modal?.type === 'doctor' && <DoctorModal act={act} onClose={() => setModal(null)} />}

      {toast && (
        <div className={`toast toast-${toast.kind}`} role="status">{toast.message}</div>
      )}
    </div>
  );
}
