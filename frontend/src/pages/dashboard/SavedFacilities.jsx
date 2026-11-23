import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { DashboardHeader } from '../../components/DashboardParts';
import { FacilityCard } from '../../components/FacilityCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { useSaved } from '../../hooks/useSaved';

export default function SavedFacilities() {
  useDocumentTitle('Saved facilities');
  const { isSaved } = useSaved();
  const result = useFetch(() => api.saved(), []);
  const items = (result.data || []).filter((f) => isSaved(f.slug));
  return (
    <>
      <DashboardHeader title="Saved facilities" description="Facilities you are considering. Remove one with the heart button." />
      {result.loading && <LoadingState rows={2} height={160} />}
      {result.error && <ErrorState error={result.error} onRetry={result.reload} />}
      {result.data && items.length === 0 && (
        <EmptyState icon={<Heart size={24} />} title="No saved facilities" action={<Link className="btn btn-primary" to="/find-care/facilities">Find facilities</Link>}>
          Save facilities while you search and they will appear here on any device you sign in from.
        </EmptyState>
      )}
      <div className="result-list">
        {items.map((f) => (
          <FacilityCard key={f.slug} facility={f} />
        ))}
      </div>
    </>
  );
}
