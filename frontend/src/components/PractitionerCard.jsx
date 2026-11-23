import { facilityDisplayName } from '../data/facilityNames';
import { Link } from 'react-router-dom';
import { Languages, MapPin, Video } from 'lucide-react';
import { DemoLabel, Rating, SourceLabel } from './Badges';

export function PractitionerCard({ practitioner: p }) {
  const initials = (p.full_name || 'Practitioner').replace(/^Dr\.\s*/, '').replace(/\(.*\)/, '').trim().split(' ').map((x) => x[0]).slice(0, 2).join('');
  return (
    <article className="practitioner-card">
      <div className="practitioner-head">
        <span className="avatar avatar-lg" aria-hidden="true">
          {initials}
        </span>
        <div>
          <h3>
            <Link to={`/find-care/specialists/${p.slug}`}>{p.full_name}</Link>
          </h3>
          <p className="small muted" style={{ margin: 0 }}>
            {p.title}
          </p>
        </div>
      </div>
      <ul className="facility-facts">
        <li>
          <MapPin size={14} aria-hidden="true" /> {p.facility ? `${facilityDisplayName(p.facility)}, ${p.town}` : p.town}
        </li>
        <li>
          <Languages size={14} aria-hidden="true" /> {(p.languages || []).join(', ') || 'Languages not listed'}
        </li>
        {p.offers_telehealth && (
          <li>
            <Video size={14} aria-hidden="true" /> Offers telehealth
          </li>
        )}
      </ul>
      <div className="row" style={{ gap: 6 }}>
        {p.registration?.status === 'matched' ? (
          <SourceLabel layer="registry">{p.registration?.body || 'Registry'} record matched</SourceLabel>
        ) : (
          <SourceLabel layer="unverified">Registration not yet checked</SourceLabel>
        )}
        {p.is_demo && <DemoLabel />}
      </div>
      <div className="practitioner-rating">
        <Rating
          rating={p.rating}
          isDemo={p.is_demo}
          demoSeed={p.slug}
        />
      </div>
    </article>
  );
}
