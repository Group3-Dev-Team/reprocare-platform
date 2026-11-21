import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { timeSlots } from '../data/labels';
import { facilityDisplayName } from '../data/facilityNames';
import { Modal } from './Modal';
import { Select, TextArea, TextInput } from './Forms';
import { Alert } from './Feedback';

const dateInKenya = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Africa/Nairobi' });
const todayIso = () => dateInKenya.format(new Date());
const maxIso = () => dateInKenya.format(new Date(Date.now() + 180 * 864e5));

/**
 * Request an appointment. The facility must confirm before it becomes an appointment,
 * and the wording everywhere says so.
 */
export function AppointmentModal({ facility, practitioner, onClose }) {
  const { user } = useAuth();
  const location = useLocation();
  const facilityName = facilityDisplayName(facility);
  const [form, setForm] = useState({ service_slug: '', preferred_date: '', preferred_time: 'morning', contact_phone: user?.phone || '', notes: '' });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(null);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  if (!user || user.role !== 'patient') {
    return (
      <Modal title="Request an appointment" description={facilityName} onClose={onClose}>
        <p>{user ? 'Appointment requests are made from a patient account.' : 'Sign in or create a free patient account to send a request and track its status.'}</p>
        {!user && (
          <div className="row">
            <Link className="btn btn-primary" to={`/sign-in?next=${encodeURIComponent(location.pathname)}`}>
              Sign in
            </Link>
            <Link className="btn btn-secondary" to={`/register?next=${encodeURIComponent(location.pathname)}`}>
              Create account
            </Link>
          </div>
        )}
      </Modal>
    );
  }

  const validate = () => {
    const next = {};
    if (!form.preferred_date) next.preferred_date = 'Choose a preferred date.';
    else if (form.preferred_date < todayIso()) next.preferred_date = 'Choose today or a later date.';
    else if (form.preferred_date > maxIso()) next.preferred_date = 'Choose a date within the next 180 days.';
    if (!/^[+\d][\d\s-]{6,}$/.test(form.contact_phone.trim())) next.contact_phone = 'Enter a phone number the facility can call, e.g. +254 712 345 678.';
    setErrors(next);
    return !Object.keys(next).length;
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!validate()) return;
    setSending(true);
    try {
      const result = await api.requestAppointment({
        facility_slug: facility.slug,
        practitioner_slug: practitioner?.slug || null,
        service_slug: form.service_slug || null,
        preferred_date: form.preferred_date,
        preferred_time: form.preferred_time,
        contact_phone: form.contact_phone.trim(),
        notes: form.notes.trim(),
      });
      setDone(result);
    } catch (err) {
      setErrors(err.fields || {});
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  if (done) {
    return (
      <Modal title="Request sent" description={facilityName} onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Done</button>}>
        <div className="confirmation">
          <CheckCircle2 size={36} color="var(--green-600)" aria-hidden="true" />
          <div>
            <p>
              Your reference is <strong>{done.reference}</strong>. This is a <strong>request</strong>, not a confirmed appointment: {facilityName} will confirm or decline it. Find updates in <Link to="/dashboard/appointments">your appointment requests</Link>.
            </p>
            <p className="small muted">If it is urgent, call the facility directly{facility.phone ? ` on ${facility.phone}` : ''}.</p>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      title="Request an appointment"
      description={`${facilityName}${practitioner ? ` · with ${practitioner.full_name}` : ''}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" form="appointment-form" type="submit" disabled={sending}>
            {sending ? 'Sending…' : 'Send request'}
          </button>
        </>
      }
    >
      <form id="appointment-form" className="form-grid" onSubmit={submit} noValidate>
        {error && (
          <div className="span-2">
            <Alert tone="danger">{error}</Alert>
          </div>
        )}
        {facility.services?.length > 0 && (
          <Select
            className="span-2"
            label="Service"
            value={form.service_slug}
            onChange={set('service_slug')}
            placeholder="Not sure yet / general consultation"
            options={facility.services.map((s) => ({ value: s.slug, label: s.name }))}
          />
        )}
        <TextInput label="Preferred date" type="date" min={todayIso()} max={maxIso()} value={form.preferred_date} onChange={set('preferred_date')} error={errors.preferred_date} required />
        <Select label="Preferred time period" hint="The facility will tell you the exact time." value={form.preferred_time} onChange={set('preferred_time')} options={Object.entries(timeSlots).map(([value, label]) => ({ value, label }))} required />
        <TextInput className="span-2" label="Phone number" type="tel" autoComplete="tel" value={form.contact_phone} onChange={set('contact_phone')} error={errors.contact_phone} hint="The facility uses this to confirm the time with you." required />
        <TextArea className="span-2" label="Anything the facility should know" value={form.notes} onChange={set('notes')} maxLength={1000} hint="Optional. Do not include detailed medical history." rows={3} />
        <div className="span-2">
          <Alert tone="info">Wait for the facility to confirm the date, then check the exact time before travelling.</Alert>
        </div>
      </form>
    </Modal>
  );
}
