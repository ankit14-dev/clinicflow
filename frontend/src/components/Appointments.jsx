import { useMemo, useState } from 'react';
import { api } from '../api.js';
import StatusBadge from './StatusBadge.jsx';
import { NEXT_ACTIONS, STATUS_LABELS, formatDay, formatTime } from '../format.js';

const FILTERS = ['ALL', ...Object.keys(STATUS_LABELS)];

export default function Appointments({ appointments, doctors, stats, act, openBooking }) {
  const [status, setStatus] = useState('ALL');
  const [doctorId, setDoctorId] = useState('');
  const [search, setSearch] = useState('');

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return appointments.filter(
      (a) =>
        (status === 'ALL' || a.status === status) &&
        (!doctorId || a.doctor.id === Number(doctorId)) &&
        (!term || a.patient.full_name.toLowerCase().includes(term) || a.reason.toLowerCase().includes(term)),
    );
  }, [appointments, status, doctorId, search]);

  const transition = (appt, next) =>
    act(() => api.appointments.update(appt.id, { status: next.status }), `${appt.patient.full_name}: ${next.label}`);

  const remove = (appt) => {
    if (window.confirm(`Delete appointment #${appt.id} for ${appt.patient.full_name}?`)) {
      act(() => api.appointments.remove(appt.id), 'Appointment deleted');
    }
  };

  return (
    <section className="card">
      <div className="toolbar">
        <div className="chips" role="tablist" aria-label="Filter by status">
          {FILTERS.map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={status === f}
              className={`chip ${status === f ? 'active' : ''}`}
              onClick={() => setStatus(f)}
            >
              {f === 'ALL' ? 'All' : STATUS_LABELS[f]}
              <span className="chip-count">{f === 'ALL' ? stats.total : stats.by_status[f] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="toolbar-inputs">
          <select value={doctorId} onChange={(e) => setDoctorId(e.target.value)} aria-label="Filter by doctor">
            <option value="">All doctors</option>
            {doctors.map((d) => <option key={d.id} value={d.id}>{d.full_name}</option>)}
          </select>
          <input
            type="search"
            placeholder="Search patient or reason"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search appointments"
          />
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          <p>No appointments match these filters.</p>
          <button className="btn btn-primary btn-small" onClick={() => openBooking()}>Book appointment</button>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>When</th>
              <th>Patient</th>
              <th>Doctor</th>
              <th>Reason</th>
              <th>Status</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((appt) => (
              <tr key={appt.id}>
                <td data-label="When">
                  <strong>{formatTime(appt.scheduled_at)}</strong>
                  <span className="muted block">{formatDay(appt.scheduled_at)} · {appt.duration_minutes} min</span>
                </td>
                <td data-label="Patient">
                  {appt.patient.full_name}
                  <span className="muted block">{appt.patient.phone}</span>
                </td>
                <td data-label="Doctor">
                  {appt.doctor.full_name}
                  <span className="muted block">{appt.doctor.specialty}</span>
                </td>
                <td data-label="Reason">{appt.reason}</td>
                <td data-label="Status"><StatusBadge status={appt.status} /></td>
                <td className="row-actions">
                  {(NEXT_ACTIONS[appt.status] ?? []).map((next) => (
                    <button
                      key={next.status}
                      className={`btn btn-small ${next.status === 'CANCELLED' ? 'btn-ghost' : ''}`}
                      onClick={() => transition(appt, next)}
                    >
                      {next.label}
                    </button>
                  ))}
                  <button className="icon-btn" onClick={() => remove(appt)} aria-label={`Delete appointment ${appt.id}`}>
                    🗑
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
