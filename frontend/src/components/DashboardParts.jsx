import { Link } from 'react-router-dom';

/** Heading block used at the top of every dashboard page. */
export function DashboardHeader({ title, description, actions }) {
  return (
    <div className="dash-header">
      <div>
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

/** A count that links to the list it summarises. Every number on a dashboard should lead somewhere useful. */
export function StatCard({ label, value, to, tone = 'blue', icon: Icon }) {
  const body = (
    <>
      {Icon && (
        <span className={`stat-icon stat-${tone}`} aria-hidden="true">
          <Icon size={20} />
        </span>
      )}
      <span className="stat-value">{value ?? '—'}</span>
      <span className="stat-label">{label}</span>
    </>
  );
  return to ? (
    <Link to={to} className="stat-card">
      {body}
    </Link>
  ) : (
    <div className="stat-card">{body}</div>
  );
}

export function Tabs({ value, onChange, options }) {
  return (
    <div className="tabs" role="tablist">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value} className="tab" onClick={() => onChange(o.value)}>
          {o.label}
          {o.count != null && <span className="tab-count">{o.count}</span>}
        </button>
      ))}
    </div>
  );
}
