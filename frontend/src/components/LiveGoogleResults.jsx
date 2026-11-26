import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, Globe2, MapPin, Star } from 'lucide-react';
import { api } from '../services/api';
import { ErrorState, LoadingState } from './Feedback';

/** Live Google Maps places with attribution. Places already in ReproCare link to their listing. Nothing is stored. */
export function LiveGoogleList({ results, selected, onSelect }) {
  return (
    <ul className="places-list">
      {results.map((p) => (
        <li key={p.place_id} className={selected === p.place_id ? 'is-selected' : ''} onMouseEnter={onSelect ? () => onSelect(p.place_id) : undefined}>
          <strong>{p.name}</strong>
          <span className="small muted">
            {p.type_label}
            {p.rating != null && <> · <Star size={12} aria-hidden="true" /> {p.rating.toFixed(1)}{p.rating_count != null && ` (${p.rating_count.toLocaleString()} Google Maps ratings)`}</>}
          </span>
          {p.facility_slug
            ? <span className="small"><span className="badge badge-success">In ReproCare directory</span> <Link to={`/facilities/${p.facility_slug}`}>Open ReproCare listing</Link></span>
            : <span className="small"><span className="badge">Live Google Maps result</span> <Link to={`/find-care/google/place/${encodeURIComponent(p.place_id)}`}>View details and reviews</Link></span>}
          <span className="small">
            <MapPin size={13} aria-hidden="true" /> {p.address}
          </span>
          {p.google_maps_uri && (
            <a href={p.google_maps_uri} target="_blank" rel="noreferrer" className="small">
              Open in Google Maps <ExternalLink size={12} aria-hidden="true" />
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}

/**
 * "More places from Google Maps" inside Find Care: one live search for the visitor's words and area, run only when
 * they ask, so the server's daily Google limit is not spent on every directory search.
 */
export function LiveGoogleResults({ query }) {
  const [state, setState] = useState({ loading: false, error: null, data: null, for: null });
  if (!query) return null;
  const current = state.for === query ? state : { loading: false, error: null, data: null };
  const run = async (pageToken) => {
    setState((s) => ({ ...s, loading: true, error: null, for: query, data: pageToken ? s.data : null }));
    try {
      const data = await api.placesSearch({ q: query, max_results: 20, page_token: pageToken });
      setState((s) => ({ loading: false, error: null, for: query,
        data: pageToken && s.data ? { ...data, results: [...s.data.results, ...data.results] } : data }));
    } catch (error) {
      setState({ loading: false, error, data: null, for: query });
    }
  };
  const extra = current.data?.results.filter((p) => !p.facility_slug).length ?? 0;
  return (
    <section className="panel live-google-results" aria-labelledby="live-google-title">
      <h2 id="live-google-title" className="h4"><Globe2 size={18} aria-hidden="true" /> More places from Google Maps</h2>
      {!current.data && !current.loading && !current.error && (
        <>
          <p className="small muted">Google Maps may list places that are not yet in the ReproCare directory. Results come live from Google and are not saved.</p>
          <button type="button" className="btn btn-secondary" onClick={() => run()}>Search Google Maps for “{query}”</button>
        </>
      )}
      {current.loading && !current.data && <LoadingState rows={2} height={80} label="Searching Google Maps" />}
      {current.error && <ErrorState error={current.error} onRetry={() => run()} />}
      {current.data && (
        <>
          <p className="small muted">
            {current.data.results.length} places, {extra} not in the ReproCare directory · <strong>{current.data.attribution}</strong>
          </p>
          <LiveGoogleList results={current.data.results} />
          {current.data.next_page_token && (
            <button type="button" className="btn btn-secondary" onClick={() => run(current.data.next_page_token)} disabled={current.loading}>
              {current.loading ? 'Loading…' : 'Load more from Google'}
            </button>
          )}
        </>
      )}
    </section>
  );
}
