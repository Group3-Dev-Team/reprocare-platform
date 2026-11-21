import { useState } from 'react';

/** A destructive button that asks for a second click in place, instead of a browser confirm() dialog. */
export function ConfirmButton({ children, question, confirmLabel, onConfirm, className = 'btn btn-danger btn-sm' }) {
  const [asking, setAsking] = useState(false);
  if (!asking) {
    return (
      <button className={className} onClick={() => setAsking(true)}>
        {children}
      </button>
    );
  }
  return (
    <span className="confirm-inline" role="group" aria-label={question}>
      <span className="small">{question}</span>
      <button
        className="btn btn-danger btn-sm"
        onClick={async () => {
          await onConfirm();
          setAsking(false);
        }}
        autoFocus
      >
        {confirmLabel}
      </button>
      <button className="btn btn-ghost btn-sm" onClick={() => setAsking(false)}>
        Keep it
      </button>
    </span>
  );
}
