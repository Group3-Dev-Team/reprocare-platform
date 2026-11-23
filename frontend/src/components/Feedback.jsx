/** Loading, empty, error and alert states, designed once and reused on every page. */
import { AlertCircle, AlertTriangle, CheckCircle2, Info, SearchX } from 'lucide-react';

export function LoadingState({ rows = 3, height = 120, label = 'Loading' }) {
  return (
    <div className="stack" role="status" aria-label={label}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height }} />
      ))}
    </div>
  );
}

export function EmptyState({ icon = <SearchX size={26} />, title, children, action, titleAs: Title = 'h3' }) {
  return (
    <div className="state">
      <div className="state-icon">{icon}</div>
      <Title className="h3">{title}</Title>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state state-error" role="alert">
      <div className="state-icon">
        <AlertCircle size={26} />
      </div>
      <h3>This section did not load</h3>
      <p>{error?.message || 'Something went wrong.'}</p>
      {onRetry && (
        <button className="btn btn-secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

const alertIcons = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: AlertCircle };

export function Alert({ tone = 'info', title, children }) {
  const Icon = alertIcons[tone];
  return (
    <div className={`alert alert-${tone}`} role={tone === 'danger' ? 'alert' : undefined}>
      <Icon size={18} aria-hidden="true" />
      <div>
        {title && <strong style={{ display: 'block', marginBottom: 2 }}>{title}</strong>}
        {children}
      </div>
    </div>
  );
}
