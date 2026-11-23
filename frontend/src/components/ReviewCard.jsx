import { facilityDisplayName } from '../data/facilityNames';
import { Link } from 'react-router-dom';
import { formatDate } from '../data/labels';
import { DemoLabel, SourceLabel, Stars } from './Badges';

export function ReviewCard({ review, showFacility = false }) {
  return (
    <article className="review-card">
      <div className="spread">
        <span className="rating">
          <Stars value={review.rating} />
          <span className="sr-only">{review.rating} out of 5</span>
        </span>
        <span className="small muted">{review.visit_month ? `Visited ${formatDate(review.visit_month, { month: 'long', year: 'numeric' })}` : formatDate(review.created_at)}</span>
      </div>
      <h3>{review.title}</h3>
      {showFacility && review.facility && (
        <p className="small" style={{ marginTop: -6 }}>
          <Link to={`/facilities/${review.facility.slug}`}>{facilityDisplayName(review.facility)}</Link>, {review.facility.town}
        </p>
      )}
      <p>{review.body}</p>
      {review.facility_reply && (
        <div className="review-reply">
          <strong>Reply from the facility</strong>
          <p>{review.facility_reply}</p>
        </div>
      )}
      <div className="row">
        <span className="small">{review.author_name}</span>
        <SourceLabel layer="patient">ReproCare review{review.service ? ` · ${review.service.name}` : ''}</SourceLabel>
        {review.is_demo && <DemoLabel />}
      </div>
    </article>
  );
}
