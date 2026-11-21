import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Accessibility, ClipboardList, CalendarCheck, Clock, Columns3, CreditCard, Languages, Mail, MapPin, Navigation, Phone, Video } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { useFetch } from '../hooks/useFetch';
import { useCompare } from '../hooks/useCompare';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { images } from '../data/images';
import { formatDate } from '../data/labels';
import { facilityDisplayName } from '../data/facilityNames';
import { serviceIcons } from '../data/serviceIcons';
import { Breadcrumbs } from '../components/PageHeader';
import { DemoLabel, Rating, RegistrationLabel, SourceLabel, Stars } from '../components/Badges';
import { FacilityTypePlaceholder } from '../components/FacilityTypePlaceholder';
import { PlanFacilityButton } from '../components/PlanFacilityButton';
import { SaveButton } from '../components/SaveButton';
import { MapView } from '../components/MapView';
import { ReviewCard } from '../components/ReviewCard';
import { ReviewForm } from '../components/ReviewForm';
import { AppointmentModal } from '../components/AppointmentModal';
import { Pagination } from '../components/Pagination';
import { EmptyState, ErrorState, LoadingState } from '../components/Feedback';
import { GoogleRatingCard, PublicFeedbackSection } from '../components/PublicFeedback';
import NotFoundPage from './NotFoundPage';
import '../styles/resource-pages.css';

export default function FacilityDetailPage() {
  const { slug } = useParams();
  return <FacilityDetails key={slug} slug={slug} />;
}

function FacilityDetails({ slug }) {
  const { user } = useAuth();
  const compare = useCompare();
  const facility = useFetch((signal) => api.facility(slug, { signal }), [slug]);
  const [reviewPage, setReviewPage] = useState(1);
  const reviews = useFetch((signal) => api.facilityReviews(slug, { page: reviewPage, page_size: 6 }, { signal }), [slug, reviewPage]);
  const ownReviews = useFetch(() => user?.role === 'patient' ? api.myReviews() : Promise.resolve([]), [user?.id, user?.role]);
  const ownReview = ownReviews.data?.find((review) => review.facility?.slug === slug);
  const publicSummary = useFetch((signal) => api.facilityPublicFeedback(slug, { signal }), [slug]);
  const [publicWritten, setPublicWritten] = useState({ facility: 0, organization: 0 });
  const [requesting, setRequesting] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const f = facility.data;
  const name = facilityDisplayName(f);
  const { hash, key: locationKey } = useLocation();
  useEffect(() => {
    if (f && hash) document.getElementById(hash.slice(1))?.scrollIntoView();
  }, [f, hash, locationKey, hash === '#google-feedback' ? publicSummary.data : null]);
  const notFound = facility.error?.status === 404;
  useDocumentTitle(
    notFound ? 'Not found' : name,
    notFound ? 'ReproCare could not find this page.' : f ? `${f.type_label} in ${f.town} with services, opening hours, sources and patient experiences.` : undefined,
    { noIndex: !f },
  );

  if (notFound) return <NotFoundPage what="facility" />;
  if (facility.error) return <div className="container section"><ErrorState error={facility.error} onRetry={facility.reload} /></div>;
  if (!f) return <div className="container section"><LoadingState rows={3} height={180} /></div>;

  const image = images[f.image_key];
  const hasCoordinates = f.latitude != null && f.longitude != null;
  const directions = hasCoordinates ? `https://www.google.com/maps/dir/?api=1&destination=${f.latitude},${f.longitude}` : null;
  const website = /^https?:\/\//i.test(f.website || '') ? f.website : null;
  const checked = f.registration.checked_on;
  const sections = [
    { id: 'about', label: 'About' },
    { id: 'services', label: 'Services' },
    { id: 'experiences', label: 'Patient Reviews', count: f.rating.count },
    { id: 'public-feedback', label: 'Public Reviews', count: publicWritten.facility, organizationCount: publicWritten.organization },
    { id: 'location', label: 'Location & Contact' },
  ];
  const activeSection = hash === '#google-feedback' ? '#public-feedback' : hash || '#about';

  return (
    <div className="facility-profile">
      <header className="detail-hero">
        <div className="container">
          <Breadcrumbs items={[{ label: 'Find care', to: '/find-care/facilities' }, { label: f.facility_type === 'laboratory' ? 'Laboratories' : 'Healthcare facilities', to: f.facility_type === 'laboratory' ? '/find-care/laboratories' : '/find-care/facilities' }, { label: name }]} />
          <div className="detail-hero-grid">
            <div className={`detail-media thumb-${f.facility_type}`}>
              {image ? <img src={image.src} alt={image.alt} /> : <FacilityTypePlaceholder type={f.facility_type} size={44} />}
            </div>
            <div>
              <p className="facility-type">{f.type_label}</p>
              <h1>{name}</h1>
              <p className="facility-place">
                <MapPin size={16} aria-hidden="true" /> {f.address || [f.area, f.town].filter(Boolean).join(', ')}
              </p>
              <div className="detail-badges">
                <RegistrationLabel status={f.registration_status} />
                {f.is_demo && <DemoLabel />}
                <a href="#experiences" className="detail-score detail-score-reprocare" title="Average of moderated reviews submitted on ReproCare">
                  <span className="detail-score-label">ReproCare rating</span>
                  <Rating rating={f.rating} />
                </a>
                {publicSummary.data?.google && (
                  <Link to="#google-feedback" className="detail-score detail-score-google" title="Google's own rating. Not a ReproCare rating.">
                    <span className="detail-score-label">On Google</span>
                    <GoogleRatingCard google={publicSummary.data.google} compact />
                  </Link>
                )}
              </div>
              <div className="row detail-actions">
                {f.accepts_appointment_requests && (!user || user.role === 'patient') && (
                  <button className="btn btn-primary" onClick={() => setRequesting(true)}>
                    <CalendarCheck size={17} aria-hidden="true" /> Request appointment
                  </button>
                )}
                {f.phone && (
                  <a className="btn btn-secondary" href={`tel:${f.phone.replace(/\s/g, '')}`}>
                    <Phone size={17} aria-hidden="true" /> Call {f.phone}
                  </a>
                )}
                {directions && (
                  <a className="btn btn-secondary" href={directions} target="_blank" rel="noreferrer">
                    <Navigation size={17} aria-hidden="true" /> Directions
                  </a>
                )}
                <SaveButton facility={f} withLabel />
                <button className="btn btn-ghost" aria-pressed={compare.has(f.slug)} onClick={() => compare.toggle(f)}>
                  <Columns3 size={17} aria-hidden="true" /> {compare.has(f.slug) ? 'In comparison' : 'Compare'}
                </button>
              </div>
              <p className="small muted">
                {f.accepts_appointment_requests
                  ? 'The facility will confirm whether it can accommodate your request.'
                  : f.phone
                    ? 'Call the facility directly for availability. Online requests are unavailable for this listing.'
                    : website
                      ? <>Online requests are unavailable. Visit the <a href={website} rel="noopener noreferrer" target="_blank">facility website</a> for booking information.</>
                      : 'Online requests and booking contact details are unavailable for this listing.'}
              </p>
            </div>
          </div>
        </div>
      </header>

      <nav className="detail-nav" aria-label="On this page">
        <div className="container">
          {sections.map(({ id, label, count, organizationCount }) => (
            <Link key={id} to={`#${id}`} aria-current={activeSection === `#${id}` ? 'location' : undefined}>
              {label}
              {!!count && <span className="detail-nav-count">{count}{id === 'public-feedback' && <span className="sr-only"> facility-specific written items</span>}</span>}
              {!!organizationCount && <span className="detail-nav-count detail-nav-count-org" >{organizationCount}<span aria-hidden="true"> org</span><span className="sr-only"> organization-wide written items</span></span>}
            </Link>
          ))}
        </div>
      </nav>

      <div className="container detail-layout">
        <div className="detail-main">
          <section className="panel" aria-labelledby="about">
            <div className="panel-title">
              <h2 id="about">About this facility</h2>
              <SourceLabel layer="provider">Stated by the facility</SourceLabel>
            </div>
            {f.description ? <p>{f.description}</p> : <p className="muted">This facility has not added a description yet. The details below come from its public listing and from the facility itself.</p>}
          </section>

          <section className="panel" aria-labelledby="services">
            <div className="panel-title">
              <h2 id="services">Services</h2>
              <SourceLabel layer="provider">Stated by the facility</SourceLabel>
            </div>
            {f.services.length ? (
              <ul className="service-list">
                {f.services.map((s) => {
                  const Icon = serviceIcons[s.slug];
                  return (
                    <li key={s.slug}>
                      {Icon && <Icon size={18} aria-hidden="true" />}
                      <Link to={`/find-care/facilities?service=${s.slug}&town=${encodeURIComponent(f.town)}`}>{s.name}</Link>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="muted">No services listed yet.</p>
            )}
            <p className="small muted" style={{ marginTop: 16, marginBottom: 0 }}>
              Services can change. Call ahead to confirm the one you need is available on the day you plan to visit.
            </p>
          </section>

          {f.lab_tests.length > 0 && (
            <section className="panel" aria-labelledby="tests">
              <div className="panel-title">
                <h2 id="tests">Laboratory tests</h2>
                <SourceLabel layer="provider">Prices stated by the laboratory</SourceLabel>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Test</th>
                      <th>Sample</th>
                      <th>Turnaround</th>
                      <th>Price</th>
                      <th>Home collection</th>
                    </tr>
                  </thead>
                  <tbody>
                    {f.lab_tests.map((t) => (
                      <tr key={t.id}>
                        <td>
                          <strong>{t.name}</strong>
                        </td>
                        <td>{t.sample_type}</td>
                        <td>{t.turnaround}</td>
                        <td>{t.price_note}</td>
                        <td>{t.home_collection ? 'Yes' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {f.practitioners.length > 0 && (
            <section className="panel" aria-labelledby="team">
              <h2 id="team">Practitioners listed here</h2>
              <ul className="people-list">
                {f.practitioners.map((p) => (
                  <li key={p.slug}>
                    <Link to={`/find-care/specialists/${p.slug}`}>{p.full_name}</Link>
                    <span className="small muted">{p.title}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="panel" aria-labelledby="experiences">
            <div className="panel-title">
              <div>
                <h2 id="experiences">Patient reviews</h2>
                <p className="panel-sub">
                  <SourceLabel layer="patient">ReproCare patient ratings</SourceLabel> Only these moderated reviews make up the ReproCare rating.
                </p>
              </div>
              {user?.role === 'patient' && (!ownReview || ownReview.status === 'rejected') && (
                <button className="btn btn-secondary btn-sm" onClick={() => setReviewing(true)}>
                  Share your experience
                </button>
              )}
              {!user && (
                <Link className="btn btn-secondary btn-sm" to={`/sign-in?next=/facilities/${f.slug}`}>
                  Sign in to share yours
                </Link>
              )}
            </div>
            {reviews.data && reviews.data.total > 0 && (
              <div className="rating-summary">
                <div>
                  <strong className="rating-big">{f.rating.average?.toFixed(1)}</strong>
                  <Stars value={f.rating.average} size={18} />
                  <p className="small muted">{f.rating.count} moderated ReproCare reviews</p>
                </div>
                <ul className="distribution" aria-label="Rating distribution">
                  {Object.entries(reviews.data.distribution).map(([star, count]) => (
                    <li key={star}>
                      <span>{star} star</span>
                      <span className="bar">
                        <span style={{ width: `${(count / reviews.data.total) * 100}%` }} />
                      </span>
                      <span>{count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="small muted">
              Reviews describe individual experiences such as waiting time and communication. They are not a measure of clinical quality, and a small number of reviews
              cannot represent every patient.
            </p>
            {ownReview?.status === 'pending' && (
              <p role="status" className="callout callout-neutral">Your review is awaiting moderation. <Link to="/dashboard/reviews">Check My reviews</Link></p>
            )}
            {reviews.loading && <LoadingState rows={2} height={110} />}
            {reviews.error && <ErrorState error={reviews.error} onRetry={reviews.reload} />}
            {reviews.data && reviews.data.total === 0 && <EmptyState title="No ReproCare reviews yet">Patients who have visited can share their experience after signing in.</EmptyState>}
            <div className="stack">
              {reviews.data?.items.map((r) => (
                <ReviewCard key={r.id} review={r} />
              ))}
            </div>
            {reviews.data && reviews.data.pages > 1 && (
              <Pagination page={reviews.data.page} pages={reviews.data.pages} total={reviews.data.total} pageSize={reviews.data.page_size} noun="reviews" onChange={setReviewPage} />
            )}
          </section>

          <PublicFeedbackSection slug={f.slug} summary={publicSummary} onWrittenCount={setPublicWritten} />
        </div>

        <aside className="detail-side">
          <section className="panel detail-visit-prep stack">
            <h2>Prepare for your visit</h2>
            <p className="small muted">Make a checklist of questions and practical reminders before you go.</p>
            <Link to={`/prepare-for-your-visit?facility=${encodeURIComponent(f.slug)}`} className="btn btn-secondary btn-sm">
              <ClipboardList size={16} aria-hidden="true" /> Open visit checklist
            </Link>
            <p className="small muted">Add this facility to a plan that stays in this browser tab.</p>
            <PlanFacilityButton slug={f.slug} />
          </section>
          <section className="panel">
            <h2>Opening hours</h2>
            <dl className="definition-list">
              <dt>Weekdays</dt>
              <dd>{f.weekday_hours || 'Not stated'}</dd>
              <dt>Saturday</dt>
              <dd>{f.saturday_hours || 'Not stated'}</dd>
              <dt>Sunday</dt>
              <dd>{f.sunday_hours || 'Not stated'}</dd>
            </dl>
            <ul className="facility-facts" style={{ marginTop: 16 }}>
              {f.open_24_hours && (
                <li>
                  <Clock size={14} aria-hidden="true" /> Open 24 hours
                </li>
              )}
              {f.offers_telehealth && (
                <li>
                  <Video size={14} aria-hidden="true" /> Telehealth consultations
                </li>
              )}
            </ul>
          </section>

          <section className="panel" id="location">
            <h2>Location</h2>
            {hasCoordinates ? (
              <MapView points={[{ id: f.slug, name, latitude: f.latitude, longitude: f.longitude, subtitle: f.town, demo: f.is_demo }]} selectedId={f.slug} height={220} zoom={14} defer label={`Map showing ${name}`} />
            ) : (
              <p className="muted">No map location stored for this facility.</p>
            )}
            <p className="small" style={{ marginTop: 12 }}>
              {f.address}
            </p>
          </section>

          <section className="panel">
            <h2>Contact and access</h2>
            <ul className="contact-list">
              {f.phone && (
                <li>
                  <Phone size={16} aria-hidden="true" /> <a href={`tel:${f.phone.replace(/\s/g, '')}`}>{f.phone}</a>
                </li>
              )}
              {f.email && (
                <li>
                  <Mail size={16} aria-hidden="true" /> <a href={`mailto:${f.email}`}>{f.email}</a>
                </li>
              )}
              {f.languages.length > 0 && (
                <li>
                  <Languages size={16} aria-hidden="true" /> {f.languages.join(', ')}
                </li>
              )}
              {f.payment_methods.length > 0 && (
                <li>
                  <CreditCard size={16} aria-hidden="true" /> {f.payment_methods.join(', ')}
                </li>
              )}
              {f.accessibility.length > 0 && (
                <li>
                  <Accessibility size={16} aria-hidden="true" /> {f.accessibility.join(', ')}
                </li>
              )}
              {!f.phone && !f.email && <li className="muted">No contact details have been provided.</li>}
            </ul>
          </section>

          <section className="panel">
            <h2>Insurance</h2>
            {f.insurers.length ? (
              <ul className="tag-list">
                {f.insurers.map((i) => (
                  <li key={i.slug} className="tag">
                    {i.name}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No insurers reported.</p>
            )}
            <p className="small muted" style={{ marginTop: 12, marginBottom: 0 }}>
              Reported by the facility. Your insurer decides what is covered.
            </p>
          </section>

          <section className="panel sources-panel">
            <h2>Where this information comes from</h2>
            <dl className="definition-list">
              <dt>Registration</dt>
              <dd>
                {f.registration.status === 'matched' ? `${f.registration.body}${f.registration.code ? `, ref. ${f.registration.code}` : ''}` : f.registration.status === 'unresolved' ? 'Possible match, not confirmed' : 'Not yet checked'}
                {checked && <span className="muted"> (checked {formatDate(checked)})</span>}
              </dd>
              <dt>Patient ratings</dt>
              <dd>ReproCare reviews only ({f.rating.count || 'none yet'})</dd>
              <dt>Public feedback</dt>
              <dd><Link to="#public-feedback">See available external sources</Link></dd>
              <dt>Listing source</dt>
              <dd>{f.source ? f.source.attribution || f.source.name : 'ReproCare'}</dd>
              <dt>Last updated</dt>
              <dd>{formatDate(f.updated_at)}</dd>
            </dl>
            <Link to={`/contact?topic=listing_correction&facility=${f.slug}`} className="btn btn-ghost btn-sm" style={{ marginTop: 12 }}>
              Report an error in this listing
            </Link>
          </section>
        </aside>
      </div>

      {requesting && <AppointmentModal facility={f} onClose={() => setRequesting(false)} />}
      {reviewing && <ReviewForm facility={f} onClose={() => setReviewing(false)} onDone={ownReviews.reload} />}
    </div>
  );
}
