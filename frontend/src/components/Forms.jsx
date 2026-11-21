/** Labelled form controls. Each one shows its hint and error text and wires up aria attributes. */
import { useId, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export function Field({ label, hint, error, children, className = '', required }) {
  const id = useId();
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined;
  return (
    <div className={`field ${className}`}>
      <label className="field-label" htmlFor={id}>
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? 'true' : undefined, required })}
      {hint && (
        <span className="field-hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
      {error && (
        <span className="field-error" id={`${id}-error`}>
          {error}
        </span>
      )}
    </div>
  );
}

export function TextInput({ label, hint, error, className, required, ...props }) {
  return (
    <Field label={label} hint={hint} error={error} className={className} required={required}>
      {(a11y) => <input className="input" {...a11y} {...props} />}
    </Field>
  );
}

export function TextArea({ label, hint, error, className, required, ...props }) {
  return (
    <Field label={label} hint={hint} error={error} className={className} required={required}>
      {(a11y) => <textarea className="textarea" {...a11y} {...props} />}
    </Field>
  );
}

export function Select({ label, hint, error, className, required, options, placeholder, ...props }) {
  return (
    <Field label={label} hint={hint} error={error} className={className} required={required}>
      {(a11y) => (
        <select className="select" {...a11y} {...props}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  );
}

export function Checkbox({ label, ...props }) {
  return (
    <label className="check">
      <input type="checkbox" {...props} />
      <span>{label}</span>
    </label>
  );
}

/** Password field with a show/hide toggle and a Caps Lock warning. Accepts the same props as TextInput. */
export function PasswordInput({ label, hint, error, className, required, ...props }) {
  const [visible, setVisible] = useState(false);
  const [caps, setCaps] = useState(false);
  const onKey = (e) => setCaps(Boolean(e.getModifierState?.('CapsLock')));
  return (
    <Field label={label} hint={caps ? <span className="caps-warning">Caps Lock is on</span> : hint} error={error} className={className} required={required}>
      {(a11y) => (
        <div className="password-field">
          <input className="input" {...a11y} {...props} type={visible ? 'text' : 'password'} onKeyUp={onKey} onKeyDown={onKey} />
          <button type="button" className="password-toggle" aria-label={visible ? 'Hide password' : 'Show password'} aria-pressed={visible} onClick={() => setVisible(!visible)}>
            {visible ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      )}
    </Field>
  );
}

/** 0–4 score for the strength meter on registration and password change. */
export function passwordStrength(value = '') {
  if (!value) return 0;
  let score = 0;
  if (value.length >= 8) score += 1;
  if (value.length >= 12) score += 1;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
  if (/\d/.test(value) && /[^A-Za-z0-9]/.test(value)) score += 1;
  if (!/\d/.test(value) || !/[a-z]/i.test(value)) score = Math.min(score, 1);
  return Math.max(1, Math.min(4, score));
}

export function StrengthMeter({ value }) {
  const level = passwordStrength(value);
  if (!value) return null;
  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  return (
    <div className="strength" data-level={level} aria-live="polite">
      <div className="strength-bar" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </div>
      <span className="strength-label">Password strength: {labels[level]}</span>
    </div>
  );
}
