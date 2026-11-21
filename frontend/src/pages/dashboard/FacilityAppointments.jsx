import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CalendarCheck, Check, Mail, Phone, X } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { appointmentStatus, formatDate, timeSlots } from '../../data/labels';
import { isCalendarDate, loadAppointmentPages, nairobiToday } from '../../data/agenda';
import { DashboardHeader, Tabs } from '../../components/DashboardParts';
import { StatusBadge } from '../../components/Badges';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { Modal } from '../../components/Modal';
import { TextArea } from '../../components/Forms';
import { Pagination } from '../../components/Pagination';
import { useToast } from '../../components/Toast';
import { AppointmentCalendar } from '../../components/AppointmentCalendar';
import '../../styles/patient-tools.css';

export default function FacilityAppointments() {
  const [params] = useSearchParams();
  const showCalendar = params.get('view') === 'schedule';
  const title = showCalendar ? 'Confirmed appointments' : 'Appointment requests';
  useDocumentTitle(title);

  return (
    <>
      <DashboardHeader title={title} description={showCalendar
        ? 'Review confirmed visits by date. The period shown is the patient’s preference.'
        : 'Confirm or decline each request. The patient sees your answer and note straight away.'} />
      <nav className="row patient-agenda-nav" aria-label="Facility appointment views">
        <Link className="btn btn-sm btn-secondary" to="/dashboard/facility/appointments"
          aria-current={!showCalendar ? 'page' : undefined}>Appointment requests</Link>
        <Link className="btn btn-sm btn-secondary" to="/dashboard/facility/appointments?view=schedule"
          aria-current={showCalendar ? 'page' : undefined}>Confirmed calendar</Link>
      </nav>
      {showCalendar ? <FacilitySchedule /> : <FacilityRequests />}
    </>
  );
}

function FacilitySchedule() {
  const result = useFetch((signal) => loadAppointmentPages(
    (page, signal) => api.facilityAppointments({ status: 'confirmed', page, page_size: 40 }, { signal }), signal,
  ), []);
  if (result.loading) return <LoadingState rows={2} height={100} label="Loading confirmed appointments" />;
  if (result.error) return <ErrorState error={result.error} onRetry={result.reload} />;
  const today = nairobiToday();
  const items = (result.data || []).filter((r) =>
    r.status === 'confirmed' && isCalendarDate(r.preferred_date) && r.preferred_date >= today,
  ).map((request) => ({ date: request.preferred_date, request }));

  return (
    <AppointmentCalendar items={items}>
      {(visible) => visible.length ? (
        <ul className="patient-agenda-list">
          {visible.map(({ date, request }) => (
            <li className="panel stack" key={request.reference}>
              <div className="spread">
                <h3 className="h3">{request.patient.full_name}</h3>
                <StatusBadge status={request.status} map={appointmentStatus} />
              </div>
              <p>{request.service?.name || 'General consultation'}</p>
              <p className="small muted"><time dateTime={date}>{formatDate(date)}</time>
                {timeSlots[request.preferred_time] && <> · Preferred period {timeSlots[request.preferred_time]}</>}
              </p>
            </li>
          ))}
        </ul>
      ) : null}
    </AppointmentCalendar>
  );
}

function FacilityRequests() {
  const [status, setStatus] = useState('requested');
  const [page, setPage] = useState(1);
  const [responding, setResponding] = useState(null); // { request, decision }
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const result = useFetch((signal) => api.facilityAppointments({ status, page }, { signal }), [status, page]);

  const respond = async () => {
    setBusy(true);
    try {
      await api.respondToAppointment(responding.request.reference, { status: responding.decision, facility_note: note.trim() });
      toast(responding.decision === 'confirmed' ? 'Request confirmed. The patient has been notified.' : 'Request declined. The patient has been notified.');
      setResponding(null);
      setNote('');
      result.reload();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Tabs value={status} onChange={(v) => { setStatus(v); setPage(1); }} options={[{ value: 'requested', label: 'Awaiting answer' }, { value: 'confirmed', label: 'Confirmed' }, { value: 'declined', label: 'Declined' }, { value: 'cancelled', label: 'Cancelled by patient' }, { value: '', label: 'All' }]} />
      {result.loading && <LoadingState rows={3} height={100} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.total === 0 && <EmptyState icon={<CalendarCheck size={24} />} title="No requests here">{status === 'requested' ? 'Every request has an answer.' : 'Nothing with this status yet.'}</EmptyState>}
      {result.data?.total > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Patient</th><th>Requested for</th><th>Service and note</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {result.data.items.map((r) => (
                <tr key={r.reference}>
                  <td>
                    <strong>{r.patient.full_name}</strong>
                    <div className="small"><Phone size={12} aria-hidden="true" /> <a href={`tel:${r.contact_phone.replace(/\s/g, '')}`}>{r.contact_phone}</a></div>
                    <div className="small"><Mail size={12} aria-hidden="true" /> {r.patient.email}</div>
                    <div className="small muted">{r.reference}</div>
                  </td>
                  <td>{formatDate(r.preferred_date, { weekday: 'short', day: 'numeric', month: 'short' })}<div className="small muted">{timeSlots[r.preferred_time]}</div></td>
                  <td>{r.service?.name || 'General consultation'}{r.practitioner && <div className="small">With {r.practitioner.full_name}</div>}{r.notes && <div className="small muted">“{r.notes}”</div>}{r.facility_note && <div className="small">Your reply: {r.facility_note}</div>}</td>
                  <td><StatusBadge status={r.status} map={appointmentStatus} /></td>
                  <td>
                    {r.status === 'requested' && (
                      <div className="row" style={{ flexWrap: 'nowrap' }}>
                        <button className="btn btn-success btn-sm" onClick={() => setResponding({ request: r, decision: 'confirmed' })}><Check size={14} aria-hidden="true" /> Confirm</button>
                        <button className="btn btn-danger btn-sm" onClick={() => setResponding({ request: r, decision: 'declined' })}><X size={14} aria-hidden="true" /> Decline</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {result.data && <Pagination page={result.data.page} pages={result.data.pages} total={result.data.total} pageSize={result.data.page_size} noun="requests" onChange={setPage} />}
      {responding && (
        <Modal
          title={responding.decision === 'confirmed' ? 'Confirm this request' : 'Decline this request'}
          description={`${responding.request.patient.full_name} · ${formatDate(responding.request.preferred_date)}`}
          onClose={() => setResponding(null)}
          footer={<><button className="btn btn-secondary" onClick={() => setResponding(null)}>Back</button><button className={`btn ${responding.decision === 'confirmed' ? 'btn-success' : 'btn-danger'}`} onClick={respond} disabled={busy}>{responding.decision === 'confirmed' ? 'Confirm request' : 'Decline request'}</button></>}
        >
          <TextArea
            label="Message to the patient"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            maxLength={1000}
            hint={responding.decision === 'confirmed' ? 'e.g. “Confirmed for 10:30 am. Please bring your antenatal booklet.”' : 'e.g. “We are fully booked that day. Please call to choose another date.”'}
          />
        </Modal>
      )}
    </>
  );
}
