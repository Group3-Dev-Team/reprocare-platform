import { Link, useSearchParams } from 'react-router-dom';
import { MessageSquareText, Search } from 'lucide-react';
import { api } from '../services/api';
import { townNames } from '../data/townNames';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/PageHeader';
import { ReviewCard } from '../components/ReviewCard';
import { Pagination } from '../components/Pagination';
import { EmptyState, ErrorState, LoadingState } from '../components/Feedback';
import '../styles/resource-pages.css';

export default function ExperiencesPage() {
  useDocumentTitle('Patient experiences', 'Read patient experiences submitted directly to ReproCare and published after moderation.');
  const [params, setParams] = useSearchParams();
  const services = useFetch(() => api.services(), []);
  const towns = useFetch(() => api.towns(), []);
  const inventory = useFetch((signal) => api.reviews({ page_size: 1 }, { signal }), []);
  const page = Math.max(1, Number.parseInt(params.get('page'), 10) || 1);
  const q = params.get('q') || '';
  const town = params.get('town') || '';
  const service = params.get('service') || '';
  const rating = params.get('rating') || '';
  const hasFilters = Boolean(q || town || service || rating);
  const results = useFetch((signal) => api.reviews({ q, town, service, rating, page, page_size: 15 }, { signal }), [q, town, service, rating, page]);
  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, String(v)) : next.delete(k)));
    if (!('page' in changes)) next.delete('page');
    setParams(next);
  };
  const data = results.loading ? null : results.data;
  const hasNoReviews = inventory.data?.total === 0;

  return (
    <div className="resource-page experience-discovery">
      <PageHeader
        title="Patient experiences"
        intro="Read what people say about waiting times, communication, privacy and cost clarity. Each review was submitted on ReproCare and published after moderation."
        crumbs={[{ label: 'Health & community', to: '/health-community/programmes' }, { label: 'Patient experiences' }]}
      />
      <div className="container resource-main experiences-layout">
        <section>
          <div className="resource-filters">
            <div className="resource-filter-heading">
              <h2>Find a patient review</h2>
              {hasFilters && <button type="button" className="btn btn-ghost btn-sm" onClick={() => setParams({})}>Clear filters</button>}
            </div>
            <form className="resource-search" role="search" onSubmit={(event) => {
              event.preventDefault();
              update({ q: String(new FormData(event.currentTarget).get('q') || '').trim() });
            }}>
              <label htmlFor="exp-q">Review topic or facility</label>
              <div className="resource-search-control">
                <input id="exp-q" name="q" className="input" key={q} defaultValue={q} maxLength={100} placeholder="e.g. waiting time" />
                <button className="btn btn-primary"><Search size={17} aria-hidden="true" /> Search</button>
              </div>
            </form>
            <div className="resource-filter-fields">
              <label>Service
                <select className="select" value={service} onChange={(event) => update({ service: event.target.value })}>
                  <option value="">Any service</option>
                  {(services.data || []).map((entry) => <option key={entry.slug} value={entry.slug}>{entry.name}</option>)}
                </select>
              </label>
              <label>Town or city
                <select className="select" value={town} onChange={(event) => update({ town: event.target.value })}>
                  <option value="">All towns</option>
                  {townNames(towns.data || []).map((name) => <option key={name}>{name}</option>)}
                </select>
              </label>
              <label>Rating
                <select className="select" value={rating} onChange={(event) => update({ rating: event.target.value })}>
                  <option value="">Any rating</option>
                  {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} star{n > 1 ? 's' : ''}</option>)}
                </select>
              </label>
            </div>
            {towns.error && <ErrorState error={towns.error} onRetry={towns.reload} />}
            {services.error && <ErrorState error={services.error} onRetry={services.reload} />}
          </div>
          <div className="resource-results-heading">
            <h2 aria-live="polite">{results.loading ? 'Loading reviews…' : results.error ? 'Patient reviews' : `${data?.total ?? 0} ${data?.total === 1 ? 'review' : 'reviews'}`}</h2>
          </div>
          {results.loading && <LoadingState rows={3} height={140} />}
          {results.error && <ErrorState error={results.error} onRetry={results.reload} />}
          {data?.total === 0 && (
            <EmptyState
              icon={<MessageSquareText size={26} />}
              title={hasNoReviews ? 'No patient reviews have been published yet' : hasFilters ? 'No reviews match these filters' : 'No patient reviews available'}
              action={hasNoReviews
                ? <Link className="btn btn-secondary" to="/find-care/facilities">Browse facilities</Link>
                : hasFilters ? <button className="btn btn-secondary" onClick={() => setParams({})}>Clear filters</button> : null}
            >
              {hasNoReviews && 'If you’ve visited a facility, you can submit a review from its listing after signing in.'}
            </EmptyState>
          )}
          {data?.items.length > 0 && <div className="review-grid">{data.items.map((review) => <ReviewCard key={review.id} review={review} showFacility />)}</div>}
          {data && <Pagination showSummary={false} page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} noun="reviews" onChange={(next) => update({ page: next })} />}
        </section>
        <aside className="resource-help">
          <h2>How to read these reviews</h2>
          <p>Use patient reports to learn about someone’s visit. They give limited information about clinical quality.</p>
          <p>ReproCare ratings come from its own published reviews. You’ll find ratings from other platforms separately on each facility page.</p>
          <Link to="/trust">How we moderate reviews</Link>
        </aside>
      </div>
    </div>
  );
}
