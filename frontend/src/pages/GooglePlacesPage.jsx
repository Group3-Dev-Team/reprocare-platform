import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink, Globe2, MapPin } from 'lucide-react';
import { api } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/PageHeader';
import { GooglePlacesMap, googleMapsAvailable } from '../components/GooglePlacesMap';
import { Alert, EmptyState, ErrorState, LoadingState } from '../components/Feedback';

/**
 * Live search of Google Places for places not yet in ReproCare.
 * Results are fetched by the backend (which holds the Places key), shown with Google attribution, and not stored.
 */
export default function GooglePlacesPage() {
  useDocumentTitle('Search Google Maps', 'Search Google Maps live for healthcare facilities that are not yet listed on ReproCare.');
  const status = useFetch(() => api.placesStatus(), []);
  const [query, setQuery] = useState('');
  const [state, setState] = useState({ loading: false, error: null, data: null });
  const [selected, setSelected] = useState(null);

  const search = async (e, pageToken) => {
    e?.preventDefault();
    if (query.trim().length < 2) return;
    setState({ loading: true, error: null, data: pageToken ? state.data : null });
    try {
      const data = await api.placesSearch({ q: query.trim(), max_results: 40, page_token: pageToken });
      setState({ loading: false, error: null, data: pageToken ? { ...data, results: [...state.data.results, ...data.results] } : data });
    } catch (error) {
      setState({ loading: false, error, data: null });
    }
  };

  return (
    <>
      <PageHeader
        title="Search Google Maps"
        intro="Look up places that are not yet on ReproCare. These results come live from Google, have not been checked by ReproCare, and are not saved to our directory."
        crumbs={[{ label: 'Find care', to: '/find-care/facilities' }, { label: 'Search Google Maps' }]}
      />
      <div className="container section-sm">
        {status.loading && <LoadingState rows={1} height={80} />}
        {status.data && !status.data.configured && (
          <EmptyState icon={<Globe2 size={26} />} title="Live Google search is not switched on for this server" action={<Link className="btn btn-primary" to="/find-care/facilities">Search ReproCare listings</Link>}>
            An administrator needs to add a Google Places API key to the backend configuration. Until then, you can search the facilities already listed on ReproCare.
          </EmptyState>
        )}
        {status.data?.configured && (
          <>
            <form className="inline-search wide" role="search" onSubmit={search}>
              <label className="sr-only" htmlFor="places-q">Search Google Maps</label>
              <input id="places-q" className="input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. maternity hospital in Nakuru" />
              <button className="btn btn-primary" disabled={state.loading}>Search</button>
            </form>
            {!googleMapsAvailable && <Alert tone="info">The map is hidden because no Google Maps browser key is configured. Results are listed with links to Google Maps.</Alert>}
            {state.loading && !state.data && <LoadingState rows={3} height={90} />}
            {state.error && <ErrorState error={state.error} onRetry={() => search()} />}
            {state.data && state.data.results.length === 0 && <EmptyState title="Google returned no places for that search">Try a broader term or a nearby town.</EmptyState>}
            {state.data && state.data.results.length > 0 && (
              <div className={googleMapsAvailable ? 'places-split' : ''}>
                <div>
                  <p className="small muted">
                    {state.data.results.length} places · <strong>{state.data.attribution}</strong>
                  </p>
                  <ul className="places-list">
                    {state.data.results.map((p) => (
                      <li key={p.place_id} className={selected === p.place_id ? 'is-selected' : ''} onMouseEnter={() => setSelected(p.place_id)}>
                        <strong>{p.name}</strong>
                        <span className="small muted">{p.type_label}</span>
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
                  {state.data.next_page_token && (
                    <button className="btn btn-secondary" onClick={(e) => search(e, state.data.next_page_token)} disabled={state.loading}>
                      {state.loading ? 'Loading…' : 'Load more from Google'}
                    </button>
                  )}
                </div>
                {googleMapsAvailable && <GooglePlacesMap places={state.data.results} selectedId={selected} onSelect={setSelected} />}
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
