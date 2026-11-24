import { facilityDisplayName } from '../data/facilityNames';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { FeedbackItems } from '../components/PublicFeedback';
import { ErrorState, LoadingState } from '../components/Feedback';
import { useFetch } from '../hooks/useFetch';
import { api } from '../services/api';

function Activity({ scope }) {
  const [organization, setOrganization] = useState('');
  const [page, setPage] = useState(1);
  const result = useFetch(() => api.facebookDemoPosts({ scope, organization, page }), [scope, organization, page]);
  return (
    <>
      {scope === 'organization' && result.data?.organizations.length > 0 && (
        <label className="field">
          Organization
          <select className="select" value={organization} onChange={(event) => { setOrganization(event.target.value); setPage(1); }}>
            <option value="">All organizations</option>
            {result.data.organizations.map((item) => <option key={item.key} value={item.key}>{item.name}</option>)}
          </select>
        </label>
      )}
      {result.data && !result.loading && <p>{result.data.total} posts · {result.data.comment_total} comments</p>}
      <FeedbackItems result={result} onPage={setPage} demo />
    </>
  );
}

function FacilityDirectory() {
  const facilities = useFetch(() => api.facebookDemoFacilities(), []);
  return (
    <section className="panel stack" aria-labelledby="demo-facility-heading">
      <h2 id="demo-facility-heading">Facilities with collected Facebook activity</h2>
      {facilities.loading ? <LoadingState rows={1} height={60} /> : facilities.error
        ? <ErrorState error={facilities.error} onRetry={facilities.reload} />
        : facilities.data?.length ? (
          <ul>
            {facilities.data.map((facility) => (
              <li key={facility.slug}>
                <Link to={`/facilities/${facility.slug}#public-feedback`}>{facilityDisplayName(facility)}</Link>
                {' · '}{facility.posts} {facility.posts === 1 ? 'post' : 'posts'}
              </li>
            ))}
          </ul>
        ) : <p>No facility pages have attributed activity in this collection.</p>}
    </section>
  );
}

export default function FacebookActivityPage() {
  const counts = useFetch(() => import.meta.env.DEV ? api.facebookDemoCounts() : Promise.resolve(null), []);
  const [scope, setScope] = useState('organization');
  return (
    <div className="container section stack">
      <h1>Public Facebook activity</h1>
      {counts.loading ? <LoadingState rows={1} height={60} /> : counts.error && counts.error.status !== 404
        ? <ErrorState error={counts.error} onRetry={counts.reload} />
        : !counts.data ? <p>Related Facebook activity is unavailable.</p> : (
          <>
            <p>Browse organization posts and other public posts that could not be matched to a specific facility. Comments are unverified.</p>
            <Link to="/find-care/facilities">Search all facilities</Link>
            <FacilityDirectory />
            <div className="chip-row" role="group" aria-label="Facebook activity scope">
              <button type="button" className="chip" aria-pressed={scope === 'organization'}
                onClick={() => setScope('organization')}>Organizations ({counts.data.organization.posts})</button>
              <button type="button" className="chip" aria-pressed={scope === 'unattributed'}
                onClick={() => setScope('unattributed')}>Posts without a facility match ({counts.data.unattributed.posts})</button>
            </div>
            {scope === 'unattributed' && <p className="callout callout-neutral">These posts could not be linked to a specific facility.</p>}
            <Activity key={scope} scope={scope} />
          </>
        )}
    </div>
  );
}
