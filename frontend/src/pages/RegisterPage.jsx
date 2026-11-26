import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { CalendarCheck, Heart, Ticket } from 'lucide-react';
import { dashboardHome, useAuth } from '../hooks/useAuth';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import familyArt from '../assets/reprocare-family-hero.webp';
import familyArtSmall from '../assets/reprocare-family-visit-small.webp';
import { Checkbox, PasswordInput, StrengthMeter, TextInput } from '../components/Forms';
import { useToast } from '../components/Toast';
import { Alert } from '../components/Feedback';
import GoogleAuthButton from '../components/GoogleAuthButton';
import { StaffAccessEnquiry } from '../components/StaffAccessEnquiry';
import { isKenyanPhone, PHONE_MESSAGE } from '../data/phone';

// only go back to pages inside the app after sign in ("/dashboard", not "//evil.example" or "https://...")
export function safeNext(value) {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\x00-\x1f\x7f\\]/.test(value)) return null;
  return value;
}

// Sign in / Create account tabs at the top of both forms
export function AuthSwitch({ active, next }) {
  const q = next ? `?next=${encodeURIComponent(next)}` : '';
  return (
    <nav className="auth-switch" aria-label="Account">
      <Link to={`/sign-in${q}`} aria-current={active === 'sign-in' ? 'page' : undefined}>
        Sign in
      </Link>
      <Link to={`/register${q}`} aria-current={active === 'register' ? 'page' : undefined}>
        Create account
      </Link>
    </nav>
  );
}

// picture and benefits on the side of the auth pages
export function AuthAside() {
  return (
    <aside className="auth-aside">
      <img src={familyArtSmall} srcSet={familyArtSmall + ' 640w, ' + familyArt + ' 1448w'} sizes="(max-width: 860px) 1px, 480px" alt="" width="1448" height="1086" loading="lazy" decoding="async" />
      <h2>One place for your next steps</h2>
      <ul>
        <li>
          <Heart size={18} aria-hidden="true" /> Save facilities you are considering
        </li>
        <li>
          <CalendarCheck size={18} aria-hidden="true" /> Send appointment requests and see when they are confirmed
        </li>
        <li>
          <Ticket size={18} aria-hidden="true" /> Keep programme registration references together
        </li>
      </ul>
    </aside>
  );
}

export default function RegisterPage() {
  useDocumentTitle('Create an account', 'Create a ReproCare patient account or learn how to request healthcare staff access.');
  const { user, register } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const nextPath = safeNext(params.get('next'));
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '', confirm: '', agree: false });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [audience, setAudience] = useState('patient');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  // already signed in, go to the dashboard
  if (user) return <Navigate to={user.role === 'patient' && nextPath ? nextPath : dashboardHome(user)} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    // check the form before sending, errors show under each field
    const next = {};
    if (form.full_name.trim().length < 2) next.full_name = 'Enter your full name.';
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) next.email = 'Enter a valid email address.';
    if (form.password.length < 8 || !/\d/.test(form.password) || !/[a-z]/i.test(form.password)) next.password = 'Use at least 8 characters, including letters and a number.';
    else if (new TextEncoder().encode(form.password).length > 72) next.password = 'This password is too long. Shorten it, especially if it includes emoji or accented characters.';
    if (form.confirm !== form.password) next.confirm = 'The passwords do not match.';
    if (form.phone.trim() && !isKenyanPhone(form.phone)) next.phone = PHONE_MESSAGE;
    if (!form.agree) next.agree = 'Please accept the terms and privacy notice.';
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    setError(null);
    try {
      const created = await register({ full_name: form.full_name.trim(), email: form.email.trim(), phone: form.phone.trim() || null, password: form.password });
      toast(`Welcome to ReproCare, ${created.full_name.split(' ')[0]}.`);
      navigate(nextPath || '/dashboard', { replace: true });
    } catch (err) {
      setError(err.status >= 500 ? 'The server could not finish creating your account. Try signing in before creating it again.' : err.message);
      setErrors(err.fields || {});
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <AuthSwitch active="register" next={nextPath} />
        <h1>Create your free account</h1>
        <div className="auth-audience" role="group" aria-label="Account type">
          <button className="btn btn-secondary btn-sm" type="button" aria-pressed={audience === 'patient'} onClick={() => setAudience('patient')}>Patient</button>
          <button className="btn btn-secondary btn-sm" type="button" aria-pressed={audience === 'staff'} onClick={() => setAudience('staff')}>Healthcare staff</button>
        </div>
        {audience === 'staff' ? (
          <StaffAccessEnquiry />
        ) : (
        <>
        <p className="muted">Create a patient account to save facilities, follow appointment requests and register for programmes.</p>
        <form className="stack" onSubmit={submit} noValidate>
          {error && <Alert tone="danger">{error}</Alert>}
          <TextInput label="Full name" autoComplete="name" autoFocus maxLength={120} value={form.full_name} onChange={set('full_name')} error={errors.full_name} required />
          <TextInput label="Email address" type="email" inputMode="email" autoComplete="email" value={form.email} onChange={set('email')} error={errors.email} required />
          <TextInput label="Phone number" type="tel" autoComplete="tel" value={form.phone} onChange={set('phone')} maxLength={40} error={errors.phone} hint="Optional. Pre-fills appointment and registration forms." />
          <div>
            <PasswordInput label="Password" autoComplete="new-password" value={form.password} onChange={set('password')} error={errors.password} hint="At least 8 characters, with letters and a number" required />
            <StrengthMeter value={form.password} />
          </div>
          <PasswordInput label="Confirm password" autoComplete="new-password" value={form.confirm} onChange={set('confirm')} error={errors.confirm} required />
          <Checkbox aria-invalid={errors.agree ? true : undefined} aria-describedby={errors.agree ? 'registration-terms-error' : undefined} checked={form.agree} onChange={set('agree')} label={<>I accept the <Link to="/terms">terms of use</Link> and have read the <Link to="/privacy">privacy notice</Link>.</>} />
          {errors.agree && <span id="registration-terms-error" className="field-error">{errors.agree}</span>}
          <button className="btn btn-primary btn-lg btn-block" disabled={busy} aria-busy={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
        </form>
        <GoogleAuthButton next={nextPath} intent="register" acceptTerms={form.agree} />
        <div className="auth-foot">
          <p className="small">
            Already have an account? <Link to={`/sign-in${nextPath ? `?next=${encodeURIComponent(nextPath)}` : ''}`}>Sign in</Link>
          </p>
          <p className="small muted">Use a unique password for your ReproCare account.</p>
        </div>
        </>
        )}
      </div>
      <AuthAside />
    </div>
  );
}