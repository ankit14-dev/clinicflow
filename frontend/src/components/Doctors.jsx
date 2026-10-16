import { api } from '../api.js';
import { initials } from '../format.js';

export default function Doctors({ doctors, appointments, act, openBooking, onAdd }) {
  const upcoming = (doctorId) =>
    appointments.filter((a) => a.doctor.id === doctorId && a.status === 'SCHEDULED' && new Date(a.scheduled_at) > new Date())
      .length;

  const toggle = (doctor) =>
    act(
      () => api.doctors.update(doctor.id, { is_active: !doctor.is_active }),
      `${doctor.full_name} is ${doctor.is_active ? 'off duty' : 'on duty'}`,
    );

  if (doctors.length === 0) {
    return (
      <section className="card empty">
        <p>No doctors yet.</p>
        <button className="btn btn-primary btn-small" onClick={onAdd}>Add a doctor</button>
      </section>
    );
  }

  return (
    <section className="doctor-grid">
      {doctors.map((doctor) => (
        <article key={doctor.id} className={`card doctor ${doctor.is_active ? '' : 'inactive'}`}>
          <div className="doctor-head">
            <span className="avatar" aria-hidden="true">{initials(doctor.full_name)}</span>
            <div>
              <h3>{doctor.full_name}</h3>
              <span className="muted">{doctor.specialty}</span>
            </div>
          </div>
          <dl className="facts">
            <div><dt>Room</dt><dd>{doctor.room || '—'}</dd></div>
            <div><dt>Upcoming</dt><dd>{upcoming(doctor.id)}</dd></div>
            <div><dt>Status</dt><dd>{doctor.is_active ? 'On duty' : 'Off duty'}</dd></div>
          </dl>
          {doctor.email && <a className="muted small" href={`mailto:${doctor.email}`}>{doctor.email}</a>}
          <div className="doctor-actions">
            <button
              className="btn btn-small btn-primary"
              disabled={!doctor.is_active}
              onClick={() => openBooking({ doctor_id: doctor.id })}
            >
              Book
            </button>
            <button className="btn btn-small btn-ghost" onClick={() => toggle(doctor)}>
              {doctor.is_active ? 'Mark off duty' : 'Mark on duty'}
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
