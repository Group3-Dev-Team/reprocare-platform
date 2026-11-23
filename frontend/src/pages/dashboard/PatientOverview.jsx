import { Link } from 'react-router-dom';
import { CalendarDays, Heart, Search, Star, Ticket } from 'lucide-react';
import { api } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { appointmentStatus, formatDate, timeSlots } from '../../data/labels';
import { facilityDisplayName } from '../../data/facilityNames';
import { DashboardHeader, StatCard } from '../../components/DashboardParts';
import { StatusBadge } from '../../components/Badges';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';

export default function PatientOverview() {
  useDocumentTitle('My ReproCare');
  const { user } = useAuth();
  const requested = useFetch(() => api.myAppointments({ status: 'requested', page_size: 4 }), []);
  const confirmed = useFetch(() => api.myAppointments({ status: 'confirmed', page_size: 4 }), []);
  const appointmentsLoading = requested.loading || confirmed.loading;
  const appointmentsError = requested.error || confirmed.error;
  const appointmentsTotal = requested.data && confirmed.data ? requested.data.total + confirmed.data.total : null;
  const saved = useFetch(() => api.saved(), []);
  const regs = useFetch(() => api.myRegistrations(), []);
  const reviews = useFetch(() => api.myReviews(), []);
  const recentOpen = [...(requested.data?.items || []), ...(confirmed.data?.items || [])]
    .sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 4);
  const activeRegs = (regs.data || []).filter((r) => r.status === 'registered');

  return (
    <>
      <div className="patient-overview-banner">
      <DashboardHeader
        title={`Hello, ${user.full_name.split(' ')[0]}`}
        description="Your requests, saved facilities and registrations in one place."
        actions={<>
          <Link to="/dashboard/appointments?view=agenda" className="btn btn-secondary"><CalendarDays size={16} aria-hidden="true" /> Patient agenda</Link>
          <Link to="/find-care/facilities" className="btn btn-primary"><Search size={16} aria-hidden="true" /> Find care</Link>
        </>}
      />
      </div>
      <div className="stat-grid">
        <StatCard icon={CalendarDays} label="Open appointment requests" value={appointmentsTotal} to="/dashboard/appointments" />
        <StatCard icon={Heart} tone="rose" label="Saved facilities" value={saved.data?.length} to="/dashboard/saved" />
        <StatCard icon={Ticket} tone="green" label="Active registrations" value={regs.data ? activeRegs.length : null} to="/dashboard/registrations" />
        <StatCard icon={Star} tone="amber" label="Reviews written" value={reviews.data?.length} to="/dashboard/reviews" />
      </div>
      <div className="dash-grid overview-grid">
        <section className="panel overview-main">
          <div className="panel-title">
            <h2>Recent open requests</h2>
            <Link to="/dashboard/appointments" className="small">View all</Link>
          </div>
          {appointmentsLoading && <LoadingState rows={2} height={70} />}
          {appointmentsError && <ErrorState error={appointmentsError} onRetry={() => { requested.reload(); confirmed.reload(); }} />}
          {appointmentsTotal === 0 && (
            <EmptyState icon={<CalendarDays size={24} />} title="No open requests" action={<Link className="btn btn-secondary btn-sm" to="/find-care/facilities?accepts_requests=true">Find facilities that take requests</Link>} />
          )}
          <ul className="item-list">
            {recentOpen.map((a) => (
              <li key={a.reference}>
                <div>
                  <strong>{facilityDisplayName(a.facility)}</strong>
                  <span className="small muted">
                    {a.service?.name || 'General consultation'} · {formatDate(a.preferred_date)}, {timeSlots[a.preferred_time]?.split(' (')[0].toLowerCase() || 'time to confirm'}
                  </span>
                </div>
                <StatusBadge status={a.status} map={appointmentStatus} />
              </li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <div className="panel-title">
            <h2>Saved facilities</h2>
            <Link to="/dashboard/saved" className="small">Manage</Link>
          </div>
          {saved.data?.length === 0 && <EmptyState icon={<Heart size={24} />} title="Nothing saved yet">Tap the heart on any facility to keep it here.</EmptyState>}
          <ul className="item-list">
            {(saved.data || []).slice(0, 4).map((f) => (
              <li key={f.slug}>
                <div>
                  <Link to={`/facilities/${f.slug}`}><strong>{facilityDisplayName(f)}</strong></Link>
                  <span className="small muted">{f.type_label} · {f.town}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <div className="panel-title">
            <h2>Programme registrations</h2>
            <Link to="/dashboard/registrations" className="small">View all</Link>
          </div>
          {regs.data && activeRegs.length === 0 && <EmptyState icon={<Ticket size={24} />} title="No upcoming programmes" action={<Link className="btn btn-secondary btn-sm" to="/health-community/programmes">Browse programmes</Link>} />}
          <ul className="item-list">
            {activeRegs.slice(0, 3).map((r) => (
              <li key={r.reference}>
                <div>
                  <Link to={`/programmes/${r.program.slug}`}><strong>{r.program.title}</strong></Link>
                  <span className="small muted">{formatDate(r.program.start_date)} · {r.program.town} · Ref {r.reference}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
