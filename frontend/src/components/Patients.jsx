import { useMemo, useState } from 'react';
import { api } from '../api.js';
import { age, formatDay } from '../format.js';

export default function Patients({ patients, appointments, act, openBooking, onAdd }) {
  const [search, setSearch] = useState('');

  const visits = useMemo(() => {
    const byPatient = {};
    for (const a of appointments) {
      const entry = (byPatient[a.patient.id] ??= { count: 0, last: null });
      entry.count += 1;
      if (a.status === 'COMPLETED' && (!entry.last || a.scheduled_at > entry.last)) entry.last = a.scheduled_at;
    }
    return byPatient;
  }, [appointments]);

  const term = search.trim().toLowerCase();
  const visible = patients.filter(
    (p) => !term || p.full_name.toLowerCase().includes(term) || p.phone.includes(term) || p.email.toLowerCase().includes(term),
  );

  const remove = (patient) => {
    if (window.confirm(`Remove ${patient.full_name}? Only possible without appointment history.`)) {
      act(() => api.patients.remove(patient.id), 'Patient removed');
    }
  };

  return (
    <section className="card">
      <div className="toolbar">
        <input
          type="search"
          placeholder="Search by name, phone or email"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search patients"
        />
        <span className="muted">{visible.length} of {patients.length} patients</span>
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          <p>{patients.length ? 'No patient matches that search.' : 'No patients registered yet.'}</p>
          <button className="btn btn-primary btn-small" onClick={onAdd}>Register patient</button>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Phone</th>
              <th>Age</th>
              <th>Visits</th>
              <th>Last completed</th>
              <th><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((p) => (
              <tr key={p.id}>
                <td data-label="Name">
                  <strong>{p.full_name}</strong>
                  {p.email && <span className="muted block">{p.email}</span>}
                </td>
                <td data-label="Phone">{p.phone}</td>
                <td data-label="Age">{age(p.date_of_birth)}</td>
                <td data-label="Visits">{visits[p.id]?.count ?? 0}</td>
                <td data-label="Last completed">{visits[p.id]?.last ? formatDay(visits[p.id].last) : '—'}</td>
                <td className="row-actions">
                  <button className="btn btn-small btn-primary" onClick={() => openBooking({ patient_id: p.id })}>Book</button>
                  <button className="icon-btn" onClick={() => remove(p)} aria-label={`Remove ${p.full_name}`}>🗑</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
