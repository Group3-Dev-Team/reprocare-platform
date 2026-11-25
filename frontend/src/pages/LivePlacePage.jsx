import { useMemo, useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { ExternalLink, Globe, MapPin, Phone } from 'lucide-react';
import { api } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/PageHeader';
import { Alert, ErrorState, LoadingState } from '../components/Feedback';
import { GooglePhoto } from '../components/GooglePhoto';
import { GoogleRatingCard, GoogleWrittenReviews } from '../components/PublicFeedback';
import { FacilityTypePlaceholder } from '../components/FacilityTypePlaceholder';

/** A place found through live Google Maps search that is not in the ReproCare directory. Nothing here is stored. */
export default function LivePlacePage() {
  const { placeId } = useParams();
  const place = useFetch((signal) => api.livePlace(placeId, { signal }), [placeId]);
  const [requested, setRequested] = useState(false);
  const reviews = useFetch((signal) => (requested ? api.livePlaceReviews(placeId, { signal }) : null), [placeId, requested]);
  const shown = useMemo(() => (reviews.data?.reviews || []).filter((r) => r.text?.trim() && r.source && r.author), [reviews.data]);
  const p = place.data;
  useDocumentTitle(p?.name || 'Google Maps listing', 'Live Google Maps details for a place that is not yet listed on ReproCare.');

  if (p?.facility_slug) return <Navigate to={`/facilities/${p.facility_slug}`} replace />;
  const crumbs = [{ label: 'Find care', to: '/find-care/facilities' }, { label: 'Search Google Maps', to: '/find-care/google' }, { label: p?.name || 'Listing' }];
  return (
    <>
      <PageHeader title={p?.name || 'Google Maps listing'} intro={p?.type_label} crumbs={crumbs} />
      <div className="container section-sm stack">
        {place.loading && <LoadingState rows={2} height={120} label="Loading from Google Maps" />}
        {place.error && <ErrorState error={place.error} onRetry={place.reload} />}
        {p && (
          <>
            <Alert tone="info" title="Live Google Maps result">
              This place is not in the ReproCare directory. The details below come live from Google Maps, have not been checked by
              ReproCare, and are not saved. Appointment requests and ReproCare patient reviews are not available for it.
            </Alert>
            <div className="detail-hero-grid">
              <div className="detail-media">
                <GooglePhoto placeId={placeId} width={800} alt={`Google Maps photo of ${p.name}`} fallback={<FacilityTypePlaceholder type="hospital" size={44} />} />
              </div>
              <div className="stack">
                {p.address && <p className="facility-place"><MapPin size={16} aria-hidden="true" /> {p.address}</p>}
                {p.phone && <p><Phone size={16} aria-hidden="true" /> <a href={`tel:${p.phone.replace(/\s+/g, '')}`}>{p.phone}</a></p>}
                {p.website && <p><Globe size={16} aria-hidden="true" /> <a href={p.website} target="_blank" rel="noopener noreferrer">Website</a></p>}
                {p.rating != null && <GoogleRatingCard google={{ rating: p.rating, rating_count: p.rating_count, attribution: p.attribution, url: p.google_maps_uri }} />}
                {p.rating == null && <p className="small muted">Google Maps shows no rating for this place.</p>}
                {p.google_maps_uri && (
                  <a className="btn btn-secondary btn-sm" href={p.google_maps_uri} target="_blank" rel="noopener noreferrer">
                    Open in Google Maps <ExternalLink size={14} aria-hidden="true" />
                  </a>
                )}
              </div>
            </div>
            <section className="stack" aria-labelledby="live-reviews">
              <h2 id="live-reviews">Google Maps reviews</h2>
              <GoogleWrittenReviews requested={requested} onRequest={() => setRequested(true)} result={reviews} reviews={shown} />
            </section>
            <p className="small muted"><Link to="/find-care/facilities">Search the ReproCare directory</Link></p>
          </>
        )}
      </div>
    </>
  );
}
