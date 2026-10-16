import StatusBadge from './StatusBadge.jsx';
import { api } from '../api.js';
import { NEXT_ACTIONS, formatDay, formatTime, isToday } from '../format.js';

function Kpi({ label, value, hint, tone }) {
  return (
    <article className={`kpi kpi-${tone}`}>
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{value}</strong>
      <span className="kpi-hint">{hint}</span>
    </article>
  );
}

export default function Dashboard({ stats, appointments, act, openBooking, onNavigate }) {
  const today = appointments.filter((a) => isToday(a.scheduled_at) && a.status !== 'CANCELLED');
  const waiting = today.filter((a) => a.status === 'CHECKED_IN');
  const nextUp = appointments
    .filter((a) => a.status === 'SCHEDULED' && new Date(a.scheduled_at) > new Date())
    .slice(0, 5);
  const maxSpecialty = Math.max(1, ...stats.by_specialty.map((s) => s.count));
  const closed = stats.completed + stats.cancelled + stats.no_show;
  const noShowRate = closed ? Math.round((stats.no_show / closed) * 100) : 0;

  const setStatus = (appt, status, label) =>
    act(() => api.appointments.update(appt.id, { status }), `${appt.patient.full_name}: ${label}`);

  return (
    <div className="dashboard">
      <section className="kpis" aria-label="Key figures">
        <Kpi label="Today" value={stats.today} hint={`${waiting.length} in the waiting room`} tone="teal" />
        <Kpi label="Upcoming" value={stats.upcoming} hint="scheduled from now on" tone="blue" />
        <Kpi label="Completed" value={stats.completed} hint={`of ${stats.total} total visits`} tone="green" />
        <Kpi label="No-show rate" value={`${noShowRate}%`} hint={`${stats.cancelled} cancelled`} tone="amber" />
      </section>

      <div className="grid-2">
        <section className="card">
          <header className="card-header">
            <h2>Today's schedule</h2>
            <button className="link" onClick={() => onNavigate('appointments')}>All appointments →</button>
          </header>
          {today.length === 0 ? (
            <div className="empty">
              <p>No appointments today.</p>
              <button className="btn btn-primary btn-small" onClick={() => openBooking()}>Book the first one</button>
            </div>
          ) : (
            <ol className="timeline">
              {today.map((appt) => (
                <li key={appt.id} className={`timeline-item status-${appt.status.toLowerCase()}`}>
                  <time>{formatTime(appt.scheduled_at)}</time>
                  <div className="timeline-body">
                    <strong>{appt.patient.full_name}</strong>
                    <span className="muted">{appt.doctor.full_name} · {appt.reason}</span>
                  </div>
                  <StatusBadge status={appt.status} />
                  <div className="row-actions">
                    {(NEXT_ACTIONS[appt.status] ?? []).slice(0, 1).map((next) => (
                      <button key={next.status} className="btn btn-small" onClick={() => setStatus(appt, next.status, next.label)}>
                        {next.label}
                      </button>
                    ))}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        <div className="stack">
          <section className="card">
            <header className="card-header"><h2>Next up</h2></header>
            {nextUp.length === 0 ? (
              <p className="empty muted">Nothing scheduled ahead.</p>
            ) : (
              <ul className="list">
                {nextUp.map((appt) => (
                  <li key={appt.id}>
                    <div>
                      <strong>{appt.patient.full_name}</strong>
                      <span className="muted">{appt.doctor.specialty}</span>
                    </div>
                    <span className="when">{formatDay(appt.scheduled_at)} · {formatTime(appt.scheduled_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <header className="card-header"><h2>Load by specialty</h2></header>
            {stats.by_specialty.length === 0 ? (
              <p className="empty muted">No bookings yet.</p>
            ) : (
              <ul className="bars">
                {stats.by_specialty.map((s) => (
                  <li key={s.specialty}>
                    <span>{s.specialty}</span>
                    <div className="bar"><div style={{ width: `${(s.count / maxSpecialty) * 100}%` }} /></div>
                    <strong>{s.count}</strong>
                  </li>
                ))}
              </ul>
            )}
            <footer className="card-footer muted">
              {stats.doctors_active} doctors on duty · {stats.patients} registered patients
            </footer>
          </section>
        </div>
      </div>
    </div>
  );
}
