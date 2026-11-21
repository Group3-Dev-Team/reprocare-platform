/** Small status and provenance labels. */
import { BadgeCheck, CircleDashed, FlaskConical, MessageSquareText, MessagesSquare, Star, Store } from 'lucide-react';

const toneClass = { success: 'badge-success', warning: 'badge-warning', danger: 'badge-danger', info: 'badge-info', neutral: '' };

export function StatusBadge({ status, map }) {
  const entry = map[status] || { label: status, tone: 'neutral' };
  return <span className={`badge ${toneClass[entry.tone]}`}>{entry.label}</span>;
}

/** Which information layer a detail comes from. See the "Our approach to trust" page. */
export function SourceLabel({ layer, children }) {
  const icons = { registry: BadgeCheck, provider: Store, patient: MessageSquareText, demo: FlaskConical, unverified: CircleDashed, external: MessagesSquare };
  const Icon = icons[layer];
  return (
    <span className={`source source-${layer}`}>
      <Icon size={13} aria-hidden="true" />
      {children}
    </span>
  );
}

export function RegistrationLabel({ status }) {
  if (status === 'matched') return <SourceLabel layer="registry">Registry record matched</SourceLabel>;
  if (status === 'unresolved') return <SourceLabel layer="unverified">Registry match unresolved</SourceLabel>;
  return <SourceLabel layer="unverified">Registry not yet checked</SourceLabel>;
}

/** Seed records are flagged in the database only; nothing is shown to visitors. Kept so existing imports keep working. */
export function DemoLabel() {
  return null;
}

export function Stars({ value, size = 15 }) {
  return (
    <span className="stars" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} size={size} className={n <= Math.round(value) ? '' : 'off'} fill="currentColor" strokeWidth={0} />
      ))}
    </span>
  );
}

// isDemo / demoSeed are accepted for backwards compatibility and ignored: ratings always come from real reviews.
// eslint-disable-next-line no-unused-vars
export function Rating({ rating, isDemo, demoSeed }) {
  const average = Number(rating?.average);
  if (!rating?.count || !Number.isFinite(average)) {
    return <span className="rating rating-unrated">No reviews yet</span>;
  }
  return (
    <span className="rating">
      <Stars value={average} />
      <strong>{average.toFixed(1)}</strong>
      <span className="rating-count">
        {rating.count} {rating.count === 1 ? 'review' : 'reviews'}
      </span>
      <span className="sr-only">Average {average.toFixed(1)} out of 5</span>
    </span>
  );
}
