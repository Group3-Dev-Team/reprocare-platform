import { facilityDisplayName } from '../data/facilityNames';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CalendarCheck, Languages, MapPin, Receipt, Video } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { formatDate } from '../data/labels';
import { PageHeader } from '../components/PageHeader';
import { DemoLabel, SourceLabel } from '../components/Badges';
import { AppointmentModal } from '../components/AppointmentModal';
import { ErrorState, LoadingState, Alert } from '../components/Feedback';
import NotFoundPage from './NotFoundPage';

export default function PractitionerDetailPage() {
  const { slug } = useParams();
  const { user } = useAuth();
  const result = useFetch(() => api.practitioner(slug), [slug]);
  const facility = useFetch(() => (result.data?.facility ? api.facility(result.data.facility.slug) : Promise.resolve(null)), [result.data?.facility?.slug]);
  const [requesting, setRequesting] = useState(false);
  const p = result.data;
  const notFound = result.error?.status === 404;
  useDocumentTitle(
    notFound ? 'Not found' : p?.full_name,
    notFound ? 'ReproCare could not find this page.' : p ? `${p.title} in ${p.town}.` : undefined,
    { noIndex: notFound },
  );

  if (notFound) return <NotFoundPage what="practitioner" />;
  if (result.error) return <div className="container section"><ErrorState error={result.error} onRetry={result.reload} /></div>;
  if (!p) return <div className="container section"><LoadingState rows={2} /></div>;

  return (
    <>
      <PageHeader title={p.full_name} intro={p.title} crumbs={[{ label: 'Find care', to: '/find-care/facilities' }, { label: 'Specialists', to: '/find-care/specialists' }, { label: p.full_name }]}>
        <div className="row" style={{ gap: 8 }}>
          {p.registration.status === 'matched' ? <SourceLabel layer="registry">{p.registration.body} record matched</SourceLabel> : <SourceLabel layer="unverified">Registration not yet checked</SourceLabel>}
          {p.is_demo && <DemoLabel />}
        </div>
      </PageHeader>
      <div className="container detail-layout section-sm">
        <div className="detail-main">
          <section className="panel">
            <div className="panel-title">
              <h2>About</h2>
              <SourceLabel layer="provider">Stated by the practitioner</SourceLabel>
            </div>
            <p>{p.bio || 'No biography provided yet.'}</p>
            <ul className="contact-list">
              <li>
                <MapPin size={16} aria-hidden="true" /> {p.facility ? <Link to={`/facilities/${p.facility.slug}`}>{facilityDisplayName(p.facility)}</Link> : 'Independent practice'}, {p.town}
              </li>
              <li>
                <Languages size={16} aria-hidden="true" /> {p.languages.join(', ')}
              </li>
              {p.offers_telehealth && (
                <li>
                  <Video size={16} aria-hidden="true" /> Offers telehealth consultations
                </li>
              )}
              {p.fee_note && (
                <li>
                  <Receipt size={16} aria-hidden="true" /> {p.fee_note}
                </li>
              )}
            </ul>
          </section>
          <section className="panel">
            <h2>Professional registration</h2>
            <dl className="definition-list">
              <dt>Register</dt>
              <dd>{p.registration.body || 'Not stated'}</dd>
              <dt>Status</dt>
              <dd>{p.registration.status === 'matched' ? 'A matching record was found' : 'Not yet checked by ReproCare'}</dd>
              {p.registration.code && (
                <>
                  <dt>Reference</dt>
                  <dd>{p.registration.code}</dd>
                </>
              )}
              {p.registration.checked_on && (
                <>
                  <dt>Checked</dt>
                  <dd>{formatDate(p.registration.checked_on)}</dd>
                </>
              )}
            </dl>
            <p className="small muted" style={{ marginTop: 12, marginBottom: 0 }}>
              A matched register record confirms identity and registration at the time of checking. It is not a recommendation.
            </p>
          </section>
        </div>
        <aside className="detail-side">
          <section className="panel">
            <h2>Next step</h2>
            {p.facility?.accepts_appointment_requests ? (
              <>
                <p className="small">Send a request to {facilityDisplayName(p.facility)}, mentioning that you would like to see {p.full_name}.</p>
                {(!user || user.role === 'patient') && (
                  <button className="btn btn-primary btn-block" onClick={() => setRequesting(true)} disabled={!facility.data}>
                    <CalendarCheck size={17} aria-hidden="true" /> Request appointment
                  </button>
                )}
              </>
            ) : (
              <Alert tone="info">Contact {p.facility ? facilityDisplayName(p.facility) : 'the practitioner'} directly to arrange a visit.</Alert>
            )}
          </section>
        </aside>
      </div>
      {requesting && facility.data && <AppointmentModal facility={facility.data} practitioner={p} onClose={() => setRequesting(false)} />}
    </>
  );
}
