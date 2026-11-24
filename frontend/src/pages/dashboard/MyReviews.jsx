import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { reviewStatus } from '../../data/labels';
import { DashboardHeader } from '../../components/DashboardParts';
import { StatusBadge } from '../../components/Badges';
import { ReviewCard } from '../../components/ReviewCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';

export default function MyReviews() {
  useDocumentTitle('My reviews');
  const result = useFetch(() => api.myReviews(), []);
  return (
    <>
      <DashboardHeader title="My reviews" description="Experiences you have shared and where they are in moderation." />
      {result.loading && <LoadingState rows={2} height={140} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.length === 0 && (
        <EmptyState icon={<Star size={24} />} title="You have not shared an experience yet" action={<Link className="btn btn-secondary" to="/dashboard/saved">Go to saved facilities</Link>}>
          Open a facility you have visited and choose “Share your experience”.
        </EmptyState>
      )}
      <div className="stack">
        {(result.data || []).map((r) => (
          <div key={r.id} className="stack-tight">
            <div className="row">
              <StatusBadge status={r.status} map={reviewStatus} />
              {r.moderation_note && <span className="small muted">Moderator: {r.moderation_note}</span>}
            </div>
            <ReviewCard review={r} showFacility />
          </div>
        ))}
      </div>
    </>
  );
}
