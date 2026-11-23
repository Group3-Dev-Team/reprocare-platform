import { Link, useSearchParams } from 'react-router-dom';
import { CalendarDays, Download } from 'lucide-react';
import { api } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { appointmentStatus, formatDate, registrationStatus, timeSlots } from '../data/labels';
import { createCalendarFile, loadAppointmentPages, upcomingAgenda } from '../data/agenda';
import { downloadFile } from '../services/downloadFile';
import { DemoLabel, StatusBadge } from './Badges';
import { EmptyState, ErrorState, LoadingState } from './Feedback';
import { AppointmentCalendar } from './AppointmentCalendar';

function exportDate(item) {
  const content = createCalendarFile(item);
  if (content) downloadFile(content, 'text/calendar;charset=utf-8', 'private-appointment.ics');
}

export function PatientAgenda() {
  const [params, setParams] = useSearchParams();
  const showCalendar = params.get('mode') === 'calendar';
  const changeMode = (mode) => {
    const next = new URLSearchParams(params);
    if (mode === 'calendar') next.set('mode', mode);
    else next.delete('mode');
    setParams(next);
  };
  const appointments = useFetch((signal) => loadAppointmentPages(
    (page, signal) => api.myAppointments({ page, page_size: 40 }, { signal }), signal,
  ), []);
  const registrations = useFetch((signal) => api.myRegistrations({ signal }), []);
  const items = upcomingAgenda(appointments.data || [], registrations.data || []);
  const loading = appointments.loading || registrations.loading;
  const hasError = appointments.error || registrations.error;

  return (
    <section className="patient-agenda stack" aria-labelledby="patient-agenda-heading">
      <div className="panel patient-agenda-overview">
        <div>
          <h2 id="patient-agenda-heading">Upcoming dates</h2>
          <p className="muted">Review requested dates, confirmed appointments and programme registrations.</p>
        </div>
        <p className="small muted">Calendar files include a generic title and the date only. Add a download to a calendar you trust. Confirm the time with the facility or programme organiser.</p>
      </div>
      <div className="row calendar-view-actions" role="group" aria-label="Agenda view">
        <button type="button" className="btn btn-secondary btn-sm" aria-pressed={!showCalendar} onClick={() => changeMode('list')}>List</button>
        <button type="button" className="btn btn-secondary btn-sm" aria-pressed={showCalendar} onClick={() => changeMode('calendar')}>Calendar</button>
      </div>
      {appointments.error && <ErrorState error={{ message: 'Appointment requests could not be loaded. ' + appointments.error.message }} onRetry={appointments.reload} />}
      {registrations.error && <ErrorState error={{ message: 'Programme registrations could not be loaded. ' + registrations.error.message }} onRetry={registrations.reload} />}
      {loading && <LoadingState rows={2} height={94} label="Loading your upcoming dates" />}
      {!showCalendar && !loading && !hasError && !items.length && (
        <EmptyState icon={<CalendarDays size={24} />} title="Nothing upcoming yet" action={<Link className="btn btn-primary" to="/dashboard/appointments">View all appointment requests</Link>}>
          Past or closed appointment requests and programme registrations stay in their respective lists.
        </EmptyState>
      )}
      {showCalendar && !loading && (!hasError || appointments.data || registrations.data) && (
        <AppointmentCalendar items={items} partial={Boolean(hasError)}>
          {(visible) => visible.length ? <AgendaList items={visible} /> : null}
        </AppointmentCalendar>
      )}
      {!showCalendar && items.length > 0 && <AgendaList items={items} />}
      <Link className="small" to="/dashboard/registrations">Manage programme registrations</Link>
    </section>
  );
}

function AgendaList({ items }) {
  return (
    <ol className="patient-agenda-list">
      {items.map((item) => {
        const appointment = item.type === 'appointment';
        const confirmed = appointment && item.status === 'confirmed';
        return (
          <li key={item.key} className="panel patient-agenda-item">
            <time className="agenda-date" dateTime={item.date}>
              <strong>{formatDate(item.date, { day: 'numeric', month: 'short' })}</strong>
              <span>{formatDate(item.date, { weekday: 'long', year: 'numeric' })}</span>
            </time>
            <div>
              <p className="small muted">{appointment ? (confirmed ? 'Confirmed date' : 'Preferred date') : 'Programme registration'}</p>
              <h3><Link to={(appointment ? '/facilities/' : '/programmes/') + item.slug}>{item.name}</Link></h3>
              <div className="row">
                <StatusBadge status={item.status} map={appointment ? appointmentStatus : registrationStatus} />
                {item.demo && <DemoLabel />}
              </div>
              <p className="small muted">
                {appointment
                  ? confirmed ? 'Contact the facility to confirm the exact time.' : (timeSlots[item.period] || 'Period to be confirmed') + '. Wait for the facility to respond.'
                  : [item.venue, [item.startsAt, item.endsAt].filter(Boolean).join(' – ')].filter(Boolean).join(' · ')}
              </p>
              {item.note && <p className="small">{item.note}</p>}
            </div>
            <div className="stack agenda-actions">
              {item.canExport && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => exportDate(item)}>
                  <Download size={16} aria-hidden="true" /> Export date (.ics)
                </button>
              )}
              {confirmed && item.phone && <a className="small" href={'tel:' + item.phone.replace(/\s/g, '')}>Call facility</a>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
