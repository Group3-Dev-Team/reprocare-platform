import { useState } from 'react';
import { Star } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { DashboardHeader } from '../../components/DashboardParts';
import { ReviewCard } from '../../components/ReviewCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { useToast } from '../../components/Toast';

export default function FacilityReviews() {
  useDocumentTitle('Patient reviews');
  const toast = useToast();
  const result = useFetch(() => api.facilityStaffReviews(), []);
  const [drafts, setDrafts] = useState({});
  const [open, setOpen] = useState(null);

  const send = async (review) => {
    const reply = (drafts[review.id] || '').trim();
    if (reply.length < 2) return toast('Write a reply first.', 'error');
    try {
      await api.replyToReview(review.id, { reply });
      toast('Reply published');
      setOpen(null);
      result.reload();
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  return (
    <>
      <DashboardHeader title="Patient reviews" description="Published reviews of your facility. You can reply publicly; you cannot edit or remove reviews." />
      {result.loading && <LoadingState rows={3} height={130} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data?.length === 0 && <EmptyState icon={<Star size={24} />} title="No published reviews yet" />}
      <div className="stack">
        {(result.data || []).map((r) => (
          <div key={r.id} className="stack-tight">
            <ReviewCard review={r} />
            {open === r.id ? (
              <div className="reply-box">
                <label className="field-label" htmlFor={`reply-${r.id}`}>Public reply</label>
                <textarea id={`reply-${r.id}`} className="textarea" rows={3} maxLength={1500} value={drafts[r.id] ?? r.facility_reply} onChange={(e) => setDrafts({ ...drafts, [r.id]: e.target.value })} placeholder="Thank the patient and explain any change you have made. Do not discuss their medical details." />
                <div className="row">
                  <button className="btn btn-primary btn-sm" onClick={() => send(r)}>Publish reply</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => setOpen(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              <button className="btn btn-secondary btn-sm" style={{ justifySelf: 'start' }} onClick={() => setOpen(r.id)}>{r.facility_reply ? 'Edit reply' : 'Reply'}</button>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
