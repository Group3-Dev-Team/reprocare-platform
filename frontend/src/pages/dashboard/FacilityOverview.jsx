import { Link } from 'react-router-dom';
import { CalendarCheck, CalendarClock, ExternalLink, MessageSquareReply, Star } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { formatDate, timeSlots } from '../../data/labels';
import { DashboardHeader, StatCard } from '../../components/DashboardParts';
import { RegistrationLabel } from '../../components/Badges';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';

export default function FacilityOverview() {
  useDocumentTitle('Facility workspace');
  const overview = useFetch(() => api.facilityOverview(), []);
  const pending = useFetch(() => api.facilityAppointments({ status: 'requested', page_size: 5 }), []);
  if (overview.error) return <ErrorState error={overview.error} onRetry={overview.reload} />;
  if (!overview.data) return <LoadingState rows={3} />;
  const { facility: f, appointments: a } = overview.data;

  return (
    <>
      <DashboardHeader
        title={f.name}
        description={`${f.type_label} · ${f.town}`}
        actions={<Link to={`/facilities/${f.slug}`} className="btn btn-secondary"><ExternalLink size={16} aria-hidden="true" /> View public listing</Link>}
      />
      <div className="stat-grid">
        <StatCard icon={CalendarClock} tone="amber" label="Requests awaiting your answer" value={a.requested} to="/dashboard/facility/appointments" />
        <StatCard icon={CalendarCheck} tone="green" label="Confirmed, upcoming" value={a.upcoming_confirmed} to="/dashboard/facility/appointments" />
        <StatCard icon={Star} label="Published reviews" value={f.rating.count} to="/dashboard/facility/reviews" />
        <StatCard icon={MessageSquareReply} tone="rose" label="Reviews without a reply" value={overview.data.reviews_awaiting_reply} to="/dashboard/facility/reviews" />
      </div>
      <div className="dash-grid two">
        <section className="panel">
          <div className="panel-title">
            <h2>Requests to answer</h2>
            <Link to="/dashboard/facility/appointments" className="small">Open all</Link>
          </div>
          {pending.data?.total === 0 && <EmptyState icon={<CalendarCheck size={24} />} title="You are up to date">New requests appear here and in your notifications.</EmptyState>}
          <ul className="item-list">
            {(pending.data?.items || []).map((r) => (
              <li key={r.reference}>
                <div>
                  <strong>{r.patient.full_name}</strong>
                  <span className="small muted">{r.service?.name || 'General consultation'} · {formatDate(r.preferred_date)}, {timeSlots[r.preferred_time].split(' (')[0].toLowerCase()}</span>
                </div>
                <span className="badge badge-warning">{r.reference}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <div className="panel-title">
            <h2>Your listing</h2>
            <Link to="/dashboard/facility/profile" className="small">Edit</Link>
          </div>
          <dl className="definition-list">
            <dt>Registration</dt>
            <dd><RegistrationLabel status={f.registration_status} /></dd>
            <dt>Weekdays</dt>
            <dd>{f.weekday_hours || 'Not stated'}</dd>
            <dt>Phone</dt>
            <dd>{f.phone || 'Not stated'}</dd>
            <dt>Online requests</dt>
            <dd>{f.accepts_appointment_requests ? 'Accepted' : 'Switched off'}</dd>
            <dt>Services</dt>
            <dd>{f.services.map((s) => s.name).join(', ')}</dd>
          </dl>
          <p className="small muted" style={{ marginTop: 12, marginBottom: 0 }}>Registration details and services are maintained by ReproCare administrators. Ask them to correct anything wrong.</p>
        </section>
      </div>
    </>
  );
}
