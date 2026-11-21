import { facilityDisplayName } from '../data/facilityNames';
import { Link } from 'react-router-dom';
import { ArrowUpRight, CalendarCheck, Clock, Columns3, MapPin, Video } from 'lucide-react';
import { images } from '../data/images';
import { useCompare, MAX_COMPARE } from '../hooks/useCompare';
import { DemoLabel, Rating, RegistrationLabel } from './Badges';
import { GoogleRatingCard } from './PublicFeedback';
import { FacilityTypePlaceholder } from './FacilityTypePlaceholder';
import { SaveButton } from './SaveButton';

/** One search result. Leads with the requested service, then practical access details and sources. */
export function FacilityCard({ facility, highlightService, selected, onSelect, onRequest }) {
  // Contact Facility leads to the listing's phone, email or website. Request appointment is shown only to
  // facilities that take ReproCare requests; there is no instant booking because no facility publishes slots.
  const hasContact = Boolean(facility.phone || facility.email || facility.website);
  const compare = useCompare();
  const image = images[facility.image_key];
  const facilityServices = Array.isArray(facility.services) ? facility.services : [];
  const facilityInsurers = Array.isArray(facility.insurers) ? facility.insurers : [];
  const services = highlightService
    ? [...facilityServices].sort((a, b) => (b.slug === highlightService) - (a.slug === highlightService))
    : facilityServices;
  const inCompare = compare.has(facility.slug);
  const canCompare = inCompare || compare.items.length < MAX_COMPARE;

  return (
    <article className={`facility-card directory-card ${selected ? 'is-selected' : ''}`} onMouseEnter={() => onSelect?.(facility.slug)}>
      <div className={`facility-thumb thumb-${facility.facility_type}`}>
        {image ? <img src={image.src} alt="" loading="lazy" /> : <FacilityTypePlaceholder type={facility.facility_type} size={28} />}
      </div>
      <div className="facility-body">
        <div className="facility-head">
          <div>
            <p className="facility-type">
              {facility.type_label}
              {facility.distance_km != null && <> · {facility.distance_km} km away</>}
            </p>
            <h3>
              <Link to={`/facilities/${facility.slug}`}>{facilityDisplayName(facility)}</Link>
            </h3>
            <p className="facility-place">
              <MapPin size={14} aria-hidden="true" />
              {[facility.area, facility.town].filter(Boolean).join(', ')}
            </p>
          </div>
          <SaveButton facility={facility} />
        </div>

        {services.length > 0 && <ul className="tag-list" aria-label="Services">
          {services.slice(0, 5).map((s) => (
            <li key={s.slug} className={`tag ${s.slug === highlightService ? 'tag-match' : ''}`}>
              {s.name}
            </li>
          ))}
          {services.length > 5 && <li className="tag tag-more">+{services.length - 5} more</li>}
        </ul>}

        <ul className="facility-facts">
          <li>
            <Clock size={14} aria-hidden="true" />
            {facility.open_24_hours ? 'Open 24 hours' : facility.weekday_hours ? `Weekdays ${facility.weekday_hours}` : 'Hours not listed'}
            {facility.open_weekends && !facility.open_24_hours ? ' · weekends' : ''}
          </li>
          {facility.offers_telehealth && (
            <li>
              <Video size={14} aria-hidden="true" /> Telehealth
            </li>
          )}
          {facilityInsurers.length > 0 && <li>Reports accepting {facilityInsurers.map((i) => i.name.replace(/ \(.*\)/, '')).slice(0, 3).join(', ')}</li>}
        </ul>

        <div className="facility-foot">
          <div className="facility-sources">
            {facility.registration_status === 'matched' && <RegistrationLabel status={facility.registration_status} />}
            {facility.is_demo && <DemoLabel />}
            <Rating rating={facility.rating} isDemo={facility.is_demo} demoSeed={facility.slug} />
          </div>
          {facility.google_rating && (
            <Link to={`/facilities/${facility.slug}#google-feedback`} aria-label="Open Google Maps ratings for this facility">
              <GoogleRatingCard google={facility.google_rating} compact />
            </Link>
          )}
          <div className="row directory-card-actions">
            <Link to={`/facilities/${facility.slug}#experiences`} className="btn btn-secondary btn-sm">
              Patient reviews
            </Link>
            <button type="button" className="btn btn-secondary btn-sm directory-compare-toggle" aria-pressed={inCompare} disabled={!canCompare}
              aria-label={`Compare ${facilityDisplayName(facility)}`} title={canCompare ? undefined : 'Remove a facility from the comparison to add another'}
              onClick={() => compare.toggle(facility)}>
              <Columns3 size={15} aria-hidden="true" /> {inCompare ? 'Added to compare' : 'Compare'}
            </button>
            {facility.accepts_appointment_requests && onRequest ? (
              <button className="btn btn-primary btn-sm" onClick={() => onRequest(facility)}>
                <CalendarCheck size={15} aria-hidden="true" /> Request appointment
              </button>
            ) : (
              <Link to={`/facilities/${facility.slug}${onRequest && hasContact ? '#location' : ''}`} className="btn btn-secondary btn-sm">
                {onRequest && hasContact ? 'Contact facility' : 'View details'} <ArrowUpRight size={15} aria-hidden="true" />
              </Link>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
