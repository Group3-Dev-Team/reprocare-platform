import { useState } from 'react';
import { Star } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { DashboardHeader, Tabs } from '../../components/DashboardParts';
import { ReviewCard } from '../../components/ReviewCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { Pagination } from '../../components/Pagination';
import { useToast } from '../../components/Toast';

export default function AdminReviews() {
  useDocumentTitle('Review moderation');
  const [status, setStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const [notes, setNotes] = useState({});
  const toast = useToast();
  const result = useFetch(() => api.adminReviews({ status, page }), [status, page]);

  const decide = async (review, decision) => {
    try {
      await api.moderateReview(review.id, { decision, note: notes[review.id] || '' });
      toast(decision === 'published' ? 'Review published' : 'Review not published. The author has been told.');
      result.reload();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <>
      <DashboardHeader title="Review moderation" description="Publish reviews that describe a real experience without personal or medical details, abuse or advertising." />
      <Tabs value={status} onChange={(v) => { setStatus(v); setPage(1); }} options={[{ value: 'pending', label: 'Awaiting moderation' }, { value: 'published', label: 'Published' }, { value: 'rejected', label: 'Not published' }]} />
      {result.loading && <LoadingState rows={2} height={160} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.total === 0 && <EmptyState icon={<Star size={24} />} title="Nothing to moderate">New reviews will appear here.</EmptyState>}
      <div className="stack">
        {(result.data?.items || []).map((r) => (
          <div key={r.id} className="moderation-item">
            <ReviewCard review={r} showFacility />
            <div className="moderation-actions">
              <label className="sr-only" htmlFor={`note-${r.id}`}>Note to the author</label>
              <input id={`note-${r.id}`} className="input" placeholder="Note to the author (optional, shown if not published)" value={notes[r.id] || ''} onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} />
              {r.status !== 'published' && <button className="btn btn-success btn-sm" onClick={() => decide(r, 'published')}>Publish</button>}
              {r.status !== 'rejected' && <button className="btn btn-danger btn-sm" onClick={() => decide(r, 'rejected')}>Do not publish</button>}
            </div>
          </div>
        ))}
      </div>
      {result.data && <Pagination page={result.data.page} pages={result.data.pages} total={result.data.total} pageSize={result.data.page_size} noun="reviews" onChange={setPage} />}
    </>
  );
}
