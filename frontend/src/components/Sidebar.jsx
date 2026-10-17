const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: '▦' },
  { id: 'appointments', label: 'Appointments', icon: '◷' },
  { id: 'doctors', label: 'Doctors', icon: '✚' },
  { id: 'patients', label: 'Patients', icon: '☺' },
];

// CI/CD stages this build went through; shown with the running commit so a deploy is visible in the UI
const PIPELINE = ['Test', 'Build', 'Scan', 'Push', 'Deploy'];

export default function Sidebar({ view, onNavigate, info, stats }) {
  const version = info?.version ?? '…';
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">+</span>
        <div>
          <strong>ClinicFlow</strong>
          <small>Sunrise Multispeciality Clinic, Pune</small>
        </div>
      </div>

      <nav className="nav" aria-label="Main">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${view === item.id ? 'active' : ''}`}
            aria-current={view === item.id ? 'page' : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <span className="nav-icon" aria-hidden="true">{item.icon}</span>
            {item.label}
            {item.id === 'appointments' && stats.today > 0 && <span className="nav-count">{stats.today}</span>}
          </button>
        ))}
      </nav>

      <div className="build-card">
        <div className="build-row">
          <span className="dot dot-live" aria-hidden="true" />
          <span>{info?.environment ?? 'connecting'}</span>
        </div>
        <div className="pipeline" aria-label="Delivery pipeline">
          {PIPELINE.map((stage) => <span key={stage} className="stage">{stage}</span>)}
        </div>
        <code title="Git commit SHA of the running backend image">build {version.slice(0, 7)}</code>
      </div>
    </aside>
  );
}
