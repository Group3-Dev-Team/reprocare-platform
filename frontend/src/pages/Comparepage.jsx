import { useState } from 'react';
import { facilityDisplayName } from '../data/facilityNames';
import { Link, useSearchParams } from 'react-router-dom';
import { Columns3 } from 'lucide-react';
import { api } from '../services/api';
import { useCompare } from '../hooks/useCompare';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { Select } from '../components/Forms';
import { PageHeader } from '../components/PageHeader';
import { DemoLabel, Rating, RegistrationLabel } from '../components/Badges';
import { Alert, EmptyState, LoadingState } from '../components/Feedback';
import { GoogleRatingCard } from '../components/PublicFeedback';
import '../styles/discovery.css';

const TOPICS = [
  ['services', 'Location and services'],
  ['access', 'Hours and appointments'],
  ['reviews', 'Ratings and feedback'],
  ['coverage', 'Insurance and costs'],
];

const CARE_GOALS = new Map([
  ['antenatal', { label: 'Plan pregnancy check-ups', purpose: 'pregnancy' }],
  ['maternity', { label: 'Plan where to give birth', purpose: 'pregnancy' }],
  ['postnatal', { label: 'Find care after a birth' }],
  ['fertility', { label: 'Discuss trying to conceive', purpose: 'fertility' }],
  ['contraception', { label: 'Explore birth control options', purpose: 'contraception' }],
  ['sti', { label: 'Find STI testing', purpose: 'screening' }],
  ['hiv', { label: 'Find HIV testing or ask about prevention', purpose: 'screening' }],
  ['cervical', { label: 'Find cervical screening', purpose: 'screening' }],
  ['ultrasound', { label: 'Find a pregnancy scan', purpose: 'pregnancy' }],
  ['gynae', { label: 'Arrange a gynaecology consultation' }],
  ['lab', { label: 'Find a lab test', purpose: 'screening' }],
]);

function CareServiceGuide({ goal, setGoal }) {
  const catalogue = useFetch(api.services);
  const services = catalogue.data || [];
  const selected = services.find((service) => service.slug === goal);
  const purpose = CARE_GOALS.get(selected?.slug)?.purpose;
  const search = selected && new URLSearchParams({ service: selected.slug });

  return (
    <section className="panel stack care-service-guide" aria-labelledby="care-service-heading">
      <div>
        <h2 id="care-service-heading">Find a service for your next visit</h2>
        <p className="muted">Choose a goal to see which service to ask a facility about.</p>
      </div>
      {catalogue.loading && <p role="status">Loading care options…</p>}
      {catalogue.error && (
        <div className="row" role="alert">
          <p>Care options could not be loaded.</p>
          <button type="button" className="btn btn-secondary btn-sm" onClick={catalogue.reload}>Try again</button>
        </div>
      )}
      {!catalogue.loading && !catalogue.error && (
        services.length ? (
          <Select className="care-service-goal" label="Care goal" value={selected ? goal : ''} placeholder="Choose a goal"
            options={services.map((service) => ({ value: service.slug, label: CARE_GOALS.get(service.slug)?.label || service.name }))}
            onChange={(event) => setGoal(event.target.value)} />
        ) : <p>There are no service categories available to search yet.</p>
      )}
      <div aria-live="polite">
        {selected && (
          <>
            <h3>{selected.name}</h3>
            <p className="muted">Ask the facility whether it offers this service, what the visit costs and how to arrange an appointment.</p>
          </>
        )}
      </div>
      <div className="row">
        {search && <Link className="btn btn-primary btn-sm" to={`/find-care/facilities?${search}`}>Search for this service</Link>}
        <Link className="btn btn-secondary btn-sm" to="/prepare-for-your-visit" state={purpose ? { purpose } : undefined}>
          {selected ? 'Prepare questions for your visit' : 'Prepare for a general consultation'}
        </Link>
      </div>
    </section>
  );
}

function ContactLinks({ facility: f }) {
  const website = f.website && /^https?:\/\//i.test(f.website) ? f.website : f.website ? `https://${f.website}` : null;
  if (!f.phone && !f.email && !website) return <p className="small muted">No contact details are recorded.</p>;
  return (
    <ul className="care-decision-contact">
      {f.phone && <li><a href={'tel:' + f.phone.replace(/[^+\d]/g, '')}>Call {f.phone}</a></li>}
      {f.email && <li><a href={`mailto:${f.email}`}>Email {f.email}</a></li>}
      {website && <li><a href={website} target="_blank" rel="noreferrer">Visit website<span className="sr-only"> (opens in a new tab)</span></a></li>}
    </ul>
  );
}

function DecisionFacts({ facility: f, topic, feedback }) {
  if (topic === 'services') {
    return (
      <>
        <p>{[f.area, f.town, f.county === f.town ? null : f.county].filter(Boolean).join(', ')}</p>
        {f.services.length > 0 ? (
          <ul className="tag-list" aria-label="Recorded services">
            {f.services.map((service) => <li key={service.slug} className="tag">{service.name}</li>)}
          </ul>
        ) : <p className="small muted">No services have been recorded. Ask the facility about the care you need.</p>}
        <RegistrationLabel status={f.registration_status} />
      </>
    );
  }
  if (topic === 'access') {
    const hours = [
      ['Weekdays', f.weekday_hours], ['Saturday', f.saturday_hours], ['Sunday', f.sunday_hours],
    ].filter(([, value]) => value);
    return (
      <>
        {f.open_24_hours ? <p>Listing reports 24-hour opening.</p> : hours.length ? (
          <dl className="care-decision-facts">
            {hours.map(([day, value]) => <div key={day}><dt>{day}</dt><dd>{value}</dd></div>)}
          </dl>
        ) : <p className="small muted">Opening hours are not recorded.</p>}
        <p>{f.accepts_appointment_requests
          ? 'Accepts ReproCare appointment requests. The facility confirms availability.'
          : 'Contact the facility directly about appointments.'}</p>
        {f.offers_telehealth && <p>Listing reports telehealth consultations.</p>}
        {f.accessibility?.length > 0 && <p className="small">Accessibility listed: {f.accessibility.join(', ')}.</p>}
        <ContactLinks facility={f} />
      </>
    );
  }
  if (topic === 'reviews') {
    const written = feedback?.data?.total_comments || 0;
    return (
      <>
        <div><span className="small muted">ReproCare patient reviews</span><br /><Rating rating={f.rating} /></div>
        {(!feedback || feedback.loading) && <p className="small muted" role="status">Loading public reviews…</p>}
        {feedback?.error && (
          <div className="row" role="alert">
            <p className="small">Public reviews could not be loaded.</p>
            <button type="button" className="btn btn-secondary btn-sm" onClick={feedback.retry}>Try again</button>
          </div>
        )}
        {feedback?.data && (
          <>
            {feedback.data.google ? <GoogleRatingCard google={feedback.data.google} compact /> : (
              <p className="small muted">No Google rating is recorded for this listing.</p>
            )}
            <p className="small">
              {written > 0
                ? `${written.toLocaleString()} written public ${written === 1 ? 'comment' : 'comments'} from linked social accounts.`
                : 'No written public comments are recorded for this listing.'}
            </p>
          </>
        )}
        <Link to={`/facilities/${f.slug}#public-feedback`}>Public reviews and original sources</Link>
      </>
    );
  }
  return (
    <>
      {f.insurers.length ? <p>Reports accepting {f.insurers.map((insurer) => insurer.name).join(', ')}.</p> : (
        <p className="small muted">Insurer acceptance is not recorded. Confirm your cover with the facility and insurer.</p>
      )}
      {f.payment_methods.length > 0 && <p>Payment methods listed: {f.payment_methods.join(', ')}.</p>}
      <p className="small muted">Ask the facility about current consultation costs.</p>
    </>
  );
}

function DecisionAssistant({ facilities, topic, onTopic, toggle, feedbackFor }) {
  return (
    <section className="stack" aria-labelledby="care-decision-heading">
      <div>
        <h2 id="care-decision-heading">What matters for this visit?</h2>
        <div className="row care-decision-topics" role="group" aria-label="Decision topic">
          {TOPICS.map(([name, label]) => (
            <button key={name} type="button" className="btn btn-secondary btn-sm" aria-pressed={topic === name} onClick={() => onTopic(name)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="care-decision-grid">
        {facilities.map((f) => (
          <article key={f.slug} className="panel care-decision-card stack">
            <header>
              <span className="small muted">{f.type_label} · {f.town}</span>
              <h3><Link to={`/facilities/${f.slug}`}>{facilityDisplayName(f)}</Link></h3>
              {f.is_demo && <DemoLabel />}
            </header>
            <DecisionFacts facility={f} topic={topic} feedback={feedbackFor(f.slug)} />
            <div className="row care-decision-actions">
              <Link className="btn btn-primary btn-sm" to={`/facilities/${f.slug}`}>Open facility</Link>
              <Link className="btn btn-secondary btn-sm" to={`/prepare-for-your-visit?facility=${encodeURIComponent(f.slug)}`}>Prepare for your visit</Link>
              <button type="button" className="btn btn-ghost btn-sm" aria-label={`Remove ${facilityDisplayName(f)}`} onClick={() => toggle(f)}>Remove</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function ComparePage() {
  useDocumentTitle('Care Decision Assistant');
  const [params, setParams] = useSearchParams();
  const [goal, setGoal] = useState('');
  const requestedTopic = params.get('topic');
  const topic = TOPICS.some(([name]) => name === requestedTopic) ? requestedTopic : 'services';
  const { items, toggle, clear } = useCompare();
  const key = items.map((i) => i.slug).join(',');
  const result = useFetch((signal) => Promise.allSettled(items.map((item) => api.facility(item.slug, { signal }))), [key]);
  const facilities = result.loading ? [] : (result.data || []).filter((entry) => entry.status === 'fulfilled').map((entry) => entry.value);
  const [retryToken, setRetryToken] = useState({});
  const feedbackKey = items.map(({ slug }) => `${slug}:${retryToken[slug] || 0}`).join(',');
  const feedback = useFetch(async (signal) => {
    if (topic !== 'reviews') return null;
    const responses = await Promise.allSettled(items.map(({ slug }) => api.facilityPublicFeedback(slug, { signal })));
    return Object.fromEntries(items.map(({ slug }, index) => [slug, responses[index]]));
  }, [feedbackKey, topic]);
  const feedbackFor = (slug) => {
    if (topic !== 'reviews') return undefined;
    const retry = () => setRetryToken((current) => ({ ...current, [slug]: (current[slug] || 0) + 1 }));
    const entry = feedback.loading ? null : feedback.data?.[slug];
    if (!entry) return { loading: true, retry };
    return entry.status === 'fulfilled' ? { data: entry.value, retry } : { error: entry.reason, retry };
  };
  const unavailable = result.loading ? [] : (result.data || []).flatMap((entry, index) => (
    entry.status === 'rejected' && items[index] ? [items[index]] : []
  ));

  return (
    <>
      <PageHeader title="Care Decision Assistant" intro="Find a service, compare facilities and prepare questions for your next visit." crumbs={[{ label: 'Find care', to: '/find-care/facilities' }, { label: 'Care Decision Assistant' }]} />
      <div className="container section-sm stack directory-compare">
        <CareServiceGuide goal={goal} setGoal={setGoal} />
        {!items.length && (
          <EmptyState icon={<Columns3 size={26} />} title="Choose facilities to weigh up" action={<Link className="btn btn-primary" to="/find-care/facilities">Find facilities</Link>}>
            Choose Compare on up to three facilities in the directory to see them side by side here.
          </EmptyState>
        )}
        {items.length > 0 && result.loading && <LoadingState rows={1} height={400} />}
        {unavailable.length > 0 && (
          <Alert tone="warning" title="Some listings could not be loaded">
            <div className="row">
              {unavailable.map((item) => <button key={item.slug} className="btn btn-secondary btn-sm" onClick={() => toggle(item)}>Remove {facilityDisplayName(item)}</button>)}
              <button className="btn btn-secondary btn-sm" onClick={result.reload}>Try again</button>
            </div>
          </Alert>
        )}
        {facilities.length > 0 && (
          <>
            <DecisionAssistant facilities={facilities} topic={topic} onTopic={(name) => {
              setParams((current) => {
                const next = new URLSearchParams(current);
                next.set('topic', name);
                next.delete('view');
                return next;
              });
            }} toggle={toggle} feedbackFor={feedbackFor} />
            <div className="row">
              <Link className="btn btn-secondary btn-sm" to="/find-care/facilities">Add another facility</Link>
              <button type="button" className="btn btn-ghost btn-sm" onClick={clear}>Clear all</button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
