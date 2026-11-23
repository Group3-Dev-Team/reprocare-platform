import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CalendarDays, Phone } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { appointmentStatus, formatDate, timeSlots } from '../../data/labels';
import { facilityDisplayName } from '../../data/facilityNames';
import { DashboardHeader, Tabs } from '../../components/DashboardParts';
import { StatusBadge } from '../../components/Badges';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { Pagination } from '../../components/Pagination';
import { useToast } from '../../components/Toast';
import { ConfirmButton } from '../../components/ConfirmButton';
import { Select, TextArea, TextInput } from '../../components/Forms';
import { PatientAgenda } from '../../components/PatientAgenda';
import '../../styles/patient-tools.css';

const dateInKenya = new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Nairobi' });
const todayIso = () => dateInKenya.format(new Date());
const maxIso = () => dateInKenya.format(new Date(Date.now() + 180 * 864e5));

export default function MyAppointments() {
  const [params] = useSearchParams();
  const showAgenda = params.get('view') === 'agenda';
  useDocumentTitle(showAgenda ? 'Patient agenda' : 'Appointment requests');

  return (
    <>
      <div className="patient-overview-banner">
        <DashboardHeader
          title={showAgenda ? 'Patient agenda' : 'Appointment requests'}
          description={showAgenda ? 'Your next visits and community programme dates.' : 'Track facility responses and confirm appointment details directly with the facility.'}
          actions={<Link to="/find-care/facilities?accepts_requests=true" className="btn btn-primary">Find facilities that take requests</Link>}
        />
      </div>
      <nav className="row patient-agenda-nav" aria-label="Appointment views">
        <Link className="btn btn-sm btn-secondary" to="/dashboard/appointments" aria-current={!showAgenda ? 'page' : undefined}>Appointment requests</Link>
        <Link className="btn btn-sm btn-secondary" to="/dashboard/appointments?view=agenda" aria-current={showAgenda ? 'page' : undefined}>Patient agenda</Link>
      </nav>
      {showAgenda ? <PatientAgenda /> : <AppointmentRequests />}
    </>
  );
}

function AppointmentRequests() {
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [changing, setChanging] = useState('');
  const toast = useToast();
  const result = useFetch((signal) => api.myAppointments({ status, page }, { signal }), [status, page]);

  const cancel = async (a) => {
    try {
      await api.cancelAppointment(a.reference);
      toast('Appointment request cancelled.');
      result.reload();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <>
      <Tabs
        value={status}
        onChange={(v) => { setStatus(v); setPage(1); }}
        options={[{ value: '', label: 'All' }, { value: 'requested', label: 'Awaiting facility' }, { value: 'confirmed', label: 'Confirmed' }, { value: 'declined', label: 'Declined' }, { value: 'cancelled', label: 'Cancelled' }]}
      />
      {result.loading && <LoadingState rows={3} height={110} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {!result.loading && result.data?.total === 0 && (
        <EmptyState icon={<CalendarDays size={24} />} title={status ? 'No requests with this status' : 'You have not sent any requests yet'} action={<Link className="btn btn-primary" to="/find-care/facilities">Browse facilities</Link>}>
          Participating facilities show “Request appointment”. Other listings may provide a phone number to arrange a visit directly.
        </EmptyState>
      )}
      <div className="stack">
        {!result.loading && (result.data?.items || []).map((a) => (
          <article key={a.reference} className="panel appointment-card">
            <div className="spread">
              <div>
                <h2 className="h3"><Link to={`/facilities/${a.facility.slug}`}>{facilityDisplayName(a.facility)}</Link></h2>
                <p className="small muted" style={{ margin: 0 }}>Reference {a.reference} · sent {formatDate(a.created_at)}</p>
              </div>
              <StatusBadge status={a.status} map={appointmentStatus} />
            </div>
            <dl className="definition-list" style={{ marginTop: 16 }}>
              <dt>Service</dt>
              <dd>{a.service?.name || 'General consultation'}{a.practitioner && ` with ${a.practitioner.full_name}`}</dd>
              <dt>{a.status === 'confirmed' ? 'Confirmed date' : 'Preferred date'}</dt>
              <dd>{formatDate(a.preferred_date, { weekday: 'long', day: 'numeric', month: 'long' })}</dd>
              <dt>{a.status === 'confirmed' ? 'Requested period' : 'Preferred period'}</dt>
              <dd>{timeSlots[a.preferred_time] || 'No period recorded'}{a.status === 'confirmed' && ' · Confirm the exact time with the facility.'}</dd>
              {a.notes && (<><dt>Your note</dt><dd>{a.notes}</dd></>)}
              {a.facility_note && (<><dt>Facility’s reply</dt><dd><strong>{a.facility_note}</strong></dd></>)}
            </dl>
            <div className="row" style={{ marginTop: 16 }}>
              {a.facility.phone && <a className="btn btn-secondary btn-sm" href={`tel:${a.facility.phone.replace(/\s/g, '')}`}><Phone size={14} aria-hidden="true" /> Call facility</a>}
              {['requested', 'confirmed'].includes(a.status) && changing !== a.reference && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setChanging(a.reference)}>
                  Request a different date
                </button>
              )}
              {['requested', 'confirmed'].includes(a.status) && (
                <ConfirmButton question="Cancel this request?" confirmLabel="Yes, cancel" onConfirm={() => cancel(a)}>
                  Cancel request
                </ConfirmButton>
              )}
            </div>
            {changing === a.reference && (
              <RescheduleForm
                appointment={a}
                onCancel={() => setChanging('')}
                onDone={() => { setChanging(''); toast('Change requested. The facility will confirm the new date.'); result.reload(); }}
              />
            )}
          </article>
        ))}
      </div>
      {result.data && <Pagination page={result.data.page} pages={result.data.pages} total={result.data.total} pageSize={result.data.page_size} noun="requests" onChange={setPage} />}
    </>
  );
}

function RescheduleForm({ appointment, onCancel, onDone }) {
  const [form, setForm] = useState({ preferred_date: '', preferred_time: appointment.preferred_time || 'morning', notes: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.preferred_date) return setError('Choose a new preferred date.');
    if (form.preferred_date < todayIso()) return setError('Choose today or a later date.');
    if (form.preferred_date > maxIso()) return setError('Choose a date within the next 180 days.');
    setBusy(true);
    setError('');
    try {
      await api.rescheduleAppointment(appointment.reference, form);
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="reschedule-form" onSubmit={submit} noValidate aria-label={`Request a different date for ${appointment.reference}`}>
      <p className="small muted">
        {appointment.status === 'confirmed'
          ? 'Your confirmed date stays on record until you send this. The request then returns to the facility for a new confirmation.'
          : 'The facility will see the new preferred date and respond.'}
      </p>
      <div className="form-grid">
        <TextInput label="New preferred date" type="date" min={todayIso()} max={maxIso()} value={form.preferred_date} onChange={set('preferred_date')} error={error} required />
        <Select label="Preferred time period" value={form.preferred_time} onChange={set('preferred_time')} options={Object.entries(timeSlots).map(([value, label]) => ({ value, label }))} required />
      </div>
      <TextArea label="Note for the facility (optional)" maxLength={1000} rows={2} value={form.notes} onChange={set('notes')} />
      <div className="row">
        <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>{busy ? 'Sending…' : 'Send change request'}</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel} disabled={busy}>Keep current date</button>
      </div>
    </form>
  );
}
