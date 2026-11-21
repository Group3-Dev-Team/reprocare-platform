import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Crosshair, Grid2X2, List, LoaderCircle, Map as MapIcon, Search, SlidersHorizontal, X } from 'lucide-react';
import { api } from '../services/api';
import { useFetch } from '../hooks/useFetch';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { facilityTypes } from '../data/labels';
import { facilityDisplayName } from '../data/facilityNames';
import { PageHeader } from '../components/PageHeader';
import { FacilityCard } from '../components/FacilityCard';
import { MapView } from '../components/MapView';
import { Pagination } from '../components/Pagination';
import { EmptyState, ErrorState, LoadingState, Alert } from '../components/Feedback';
import { AppointmentModal } from '../components/AppointmentModal';
import '../styles/discovery.css';

const PAGE_SIZE = 15;
const URL_LOCATION_KEYS = ['lat', 'lng', 'radius_km'];
const RADII = ['5', '10', '25', '50', '100'];

function pointFromUrl(params) {
  const lat = params.get('lat')?.trim();
  const lng = params.get('lng')?.trim();
  if (!lat || !lng || !(Math.abs(Number(lat)) <= 90 && Math.abs(Number(lng)) <= 180)) return null;
  return { lat: Number(lat), lng: Number(lng) };
}
const COVERAGE_FIELDS = ['service', 'insurer', 'telehealth', 'accepts_requests', 'verified_only', 'has_patient_reviews', 'has_public_feedback', 'has_google_rating'];
const REVIEW_FILTERS = [
  ['has_patient_reviews', 'Has ReproCare patient reviews'],
  ['has_public_feedback', 'Has public written feedback'],
  ['has_google_rating', 'Has Google Maps ratings'],
];
const MINIMUM_GOOGLE_RATINGS = ['3', '3.5', '4', '4.5', '5'];
const SORTS = [
  ['relevance', 'Most relevant'],
  ['completeness', 'Most complete listings'],
  ['name', 'Name (A–Z)'],
  ['name_desc', 'Name (Z–A)'],
  ['google_rating', 'Highest Google Maps rating'],
  ['google_count', 'Most Google Maps ratings'],
  ['rating', 'Highest ReproCare patient rating'],
  ['review_count', 'Most ReproCare patient reviews'],
];
const COVERAGE_LABELS = {
  telehealth: 'Remote consultations',
  accepts_requests: 'ReproCare appointment requests',
  verified_only: 'Registry matches',
  has_patient_reviews: 'published ReproCare patient reviews',
  has_public_feedback: 'published facility-specific public feedback',
  has_google_rating: 'Google Maps ratings',
};

function positivePage(value) {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1;
}
const FLAGS = [
  ['open_weekends', 'Open at weekends'],
  ['open_24_hours', 'Open 24 hours'],
  ['telehealth', 'Remote consultations'],
  ['accepts_requests', 'Accepts ReproCare requests'],
  ['verified_only', 'Registry record matched'],
];

const copy = {
  facilities: {
    title: 'Find Care',
    intro: 'Explore healthcare facilities by location, service and access needs.',
    crumb: 'Healthcare facilities',
  },
  insurance: {
    title: 'Find care by insurer',
    intro: 'Facilities that report accepting SHA or a private insurer. Acceptance is what facilities tell us: confirm your cover with your insurer before treatment.',
    crumb: 'Care by insurer',
  },
  map: {
    title: 'Map of facilities',
    intro: 'Explore facilities with recorded coordinates. Choose a point on the map or use your location to see distances.',
    crumb: 'Facility map',
  },
};

/** Facility discovery. One component serves three entry points: the directory, insurer search and the map. */
export default function FindCarePage({ variant = 'facilities' }) {
  const text = copy[variant];
  useDocumentTitle(text.title, text.intro);
  const [params, setParams] = useSearchParams();
  const [showFilters, setShowFilters] = useState(false);
  const [selected, setSelected] = useState(null);
  const [requesting, setRequesting] = useState(null);
  const [location, setLocation] = useState({ pending: false, message: '' });
  const [point, setPoint] = useState(() => pointFromUrl(params));
  const [radius, setRadius] = useState(() => {
    const previousRadius = params.get('radius_km') || '';
    return Number(previousRadius) > 0 && Number(previousRadius) <= 1000 ? previousRadius : '';
  });
  const [moreOpen, setMoreOpen] = useState(() => typeof window === 'undefined' || window.innerWidth > 960
    || ['facility_type', 'min_google_rating', ...FLAGS.map(([name]) => name), ...REVIEW_FILTERS.map(([name]) => name)].some((name) => params.has(name)));
  const pendingLocation = useRef(0);
  const latestParams = useRef(params);
  const filterTrigger = useRef(null);
  const filterRef = useRef(null);
  const filterScrim = useRef(null);
  latestParams.current = params;

  const viewParam = params.get('view');
  const view = ['list', 'grid', 'map'].includes(viewParam) ? viewParam : variant === 'map' ? 'map' : 'list';
  const page = positivePage(params.get('page'));
  const requestedSort = params.get('sort');
  const explicitSort = requestedSort === 'distance' || SORTS.some(([name]) => name === requestedSort) ? requestedSort : null;
  const center = point ? [point.lat, point.lng] : null;
  const sort = explicitSort === 'distance' && !center ? 'relevance' : explicitSort || (center ? 'distance' : 'relevance');
  const filters = Object.fromEntries(params);
  delete filters.page;
  delete filters.view;
  URL_LOCATION_KEYS.forEach((key) => delete filters[key]);
  if (point) {
    filters.lat = point.lat;
    filters.lng = point.lng;
    if (radius) filters.radius_km = radius;
  }
  filters.sort = sort;

  useEffect(() => {
    if (!URL_LOCATION_KEYS.some((key) => params.has(key))) return;
    const next = new URLSearchParams(params);
    URL_LOCATION_KEYS.forEach((key) => next.delete(key));
    latestParams.current = next;
    setParams(next, { replace: true });
  }, [params, setParams]);

  const services = useFetch(() => api.services(), []);
  const insurers = useFetch(() => api.insurers(), []);
  const counties = useFetch(() => api.counties(), []);
  const filterKey = JSON.stringify(filters);
  const resultKey = JSON.stringify([filterKey, page]);
  const results = useFetch(async (signal) => ({
    key: resultKey,
    value: await api.facilities({ ...filters, page, page_size: PAGE_SIZE }, { signal }),
  }), [resultKey]);
  const markerKey = JSON.stringify([filterKey, view]);
  const markers = useFetch(async (signal) => ({
    key: markerKey,
    items: view === 'map' ? await api.facilityMarkers(filters, { signal }) : [],
  }), [markerKey]);
  const data = !results.loading && results.data?.key === resultKey ? results.data.value : null;
  const resultsPending = results.loading || (!results.error && !data);
  const mapPending = markers.loading || (!markers.error && markers.data?.key !== markerKey);
  const coverageFilters = COVERAGE_FIELDS.filter((field) => filters[field] && filters[field] !== 'false')
    .map((field) => [field, filters[field]]);
  const coverageKey = JSON.stringify(coverageFilters);
  const needsCoverage = data?.total === 0 && coverageFilters.length > 0;
  const coverage = useFetch(async (signal) => {
    if (!needsCoverage) return null;
    const checks = await Promise.allSettled(coverageFilters.map(([field, value]) => (
      api.facilities({ [field]: value, page_size: 1 }, { signal })
    )));
    return {
      key: coverageKey,
      uncovered: coverageFilters.filter((_, index) => checks[index].status === 'fulfilled' && checks[index].value.total === 0)
        .map(([field]) => field),
    };
  }, [needsCoverage, coverageKey]);
  const coveragePending = needsCoverage && (coverage.loading || coverage.data?.key !== coverageKey);
  const uncovered = needsCoverage && !coveragePending ? coverage.data?.uncovered || [] : [];
  const moreCount = ['facility_type', 'min_google_rating', ...FLAGS.map(([name]) => name), ...REVIEW_FILTERS.map(([name]) => name)]
    .filter((key) => filters[key] && filters[key] !== 'false').length;

  function update(changes, { keepPage = false } = {}) {
    const next = new URLSearchParams(latestParams.current);
    URL_LOCATION_KEYS.forEach((key) => next.delete(key));
    Object.entries(changes).forEach(([key, value]) => {
      if (value === '' || value === false || value == null) next.delete(key);
      else next.set(key, String(value));
    });
    if (!keepPage && !('page' in changes)) next.delete('page');
    latestParams.current = next;
    setParams(next);
  }

  function cancelLocation() {
    pendingLocation.current += 1;
    setLocation({ pending: false, message: '' });
  }

  function clearPoint() {
    cancelLocation();
    setPoint(null);
    setRadius('');
  }

  function clearAll() {
    clearPoint();
    const next = new URLSearchParams();
    if (params.has('view')) next.set('view', view);
    if (explicitSort && explicitSort !== 'distance') next.set('sort', explicitSort);
    latestParams.current = next;
    setParams(next);
  }

  function chooseCounty(county) {
    clearPoint();
    update({ county, town: '', sort: explicitSort === 'distance' ? '' : explicitSort });
  }

  function applyPoint(lat, lng, nextRadius = '') {
    setPoint({ lat, lng });
    setRadius(nextRadius);
    update({ town: '', county: '' });
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setLocation({ pending: false, message: 'Your browser cannot share location. Choose a county or select a point on the map.' });
      return;
    }
    const request = ++pendingLocation.current;
    setLocation({ pending: true, message: '' });
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (pendingLocation.current !== request) return;
        setLocation({ pending: false, message: 'Location selected. Choose a distance limit to search nearby.' });
        applyPoint(coords.latitude, coords.longitude);
      },
      (error) => {
        if (pendingLocation.current !== request) return;
        setLocation({ pending: false, message: error.code === 1
          ? 'Location access was declined. Allow it in your browser settings to retry, or choose a county.'
          : 'We could not determine your location. Try again or choose a county.' });
      },
      { timeout: 10000, maximumAge: 60000 },
    );
  }

  function onPick(lat, lng) {
    cancelLocation();
    applyPoint(lat, lng, radius || '25');
  }

  function closeFilters() {
    setShowFilters(false);
  }

  useDialogFocus(filterRef, showFilters, closeFilters, {
    initialFocus: '.filters-close',
    returnFocus: filterTrigger,
    allowOutside: filterScrim,
  });

  useEffect(() => () => { pendingLocation.current += 1; }, []);

  const points = useMemo(
    () =>
      (mapPending ? [] : markers.data?.items || []).map((m) => ({
        id: m.slug,
        name: facilityDisplayName(m),
        latitude: m.latitude,
        longitude: m.longitude,
        subtitle: `${facilityTypes.find((t) => t.value === m.facility_type)?.label} · ${m.town}`,
        href: `/facilities/${m.slug}`,
      })),
    [mapPending, markers.data],
  );

  const activeCount = Number(!!point) + Object.keys(filters).filter((key) => key !== 'sort' && !URL_LOCATION_KEYS.includes(key)
    && filters[key] && filters[key] !== 'false').length;
  const filterPanel = (
    <aside ref={filterRef} tabIndex={-1} className={`filters ${showFilters ? 'is-open' : ''}`} role={showFilters ? 'dialog' : undefined} aria-modal={showFilters || undefined} aria-label="Filters" id="directory-filters">
      <div className="filters-head">
        <h2>Filter facilities</h2>
        <button className="icon-btn filters-close" aria-label="Close filters" onClick={closeFilters}>
          <X size={18} />
        </button>
      </div>
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          update({ q: new FormData(e.currentTarget).get('q').trim() });
        }}
      >
        <label className="field">
          <span className="field-label">Name, area or service</span>
          <span className="search-input">
            <Search size={17} aria-hidden="true" />
            <input className="input" name="q" type="search" maxLength={100} enterKeyHint="search" defaultValue={params.get('q') || ''} key={params.get('q')} placeholder="e.g. Kilimani or family planning" />
            <button className="btn btn-primary btn-sm" type="submit">
              Search
            </button>
          </span>
        </label>
      </form>
      <label className="field">
        <span className="field-label">Service</span>
        <select className="select" aria-label="Service" value={params.get('service') || ''} onChange={(e) => update({ service: e.target.value })}>
          <option value="">Any service</option>
          {(services.data || []).map((s) => (
            <option key={s.slug} value={s.slug}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="field-label">County</span>
        <select
          className="select"
          aria-label="County"
          value={params.get('county') || ''}
          onChange={(e) => chooseCounty(e.target.value)}
        >
          <option value="">All counties</option>
          {(counties.data || []).map((c) => (
            <option key={c.county} value={c.county}>
              {c.county} ({c.facility_count})
            </option>
          ))}
        </select>
      </label>
      <div className="directory-location">
        <button type="button" className="btn btn-secondary btn-block" onClick={useMyLocation} disabled={location.pending}>
          {location.pending ? <LoaderCircle size={16} aria-hidden="true" className="directory-spinner" /> : <Crosshair size={16} aria-hidden="true" />}
          {location.pending ? 'Finding your location…' : 'Use my location'}
        </button>
        <div className="small muted" role="status">{location.message}</div>
        {point && (
          <label className="field directory-radius">
            <span className="field-label">Distance limit</span>
            <select className="select" value={radius} onChange={(e) => { setRadius(e.target.value); update({}); }}>
              <option value="">Any distance</option>
              {[...new Set([...RADII, ...(radius ? [radius] : [])])].sort((a, b) => Number(a) - Number(b)).map((km) => (
                <option key={km} value={km}>Within {km} km</option>
              ))}
            </select>
          </label>
        )}
      </div>
      <label className="field">
        <span className="field-label">Insurer {variant === 'insurance' && <span className="badge badge-info">Start here</span>}</span>
        <select className="select" aria-label="Insurer" value={params.get('insurer') || ''} onChange={(e) => update({ insurer: e.target.value })}>
          <option value="">All insurers</option>
          {(insurers.data || []).map((i) => (
            <option key={i.slug} value={i.slug}>
              {i.name}
            </option>
          ))}
        </select>
      </label>
      <details className="filter-more" open={moreOpen} onToggle={(e) => setMoreOpen(e.currentTarget.open)}>
        <summary>
          More filters
          {moreCount > 0 && <span className="filter-more-count">{moreCount}</span>}
        </summary>
        <div className="stack">
          <label className="field">
            <span className="field-label">Facility type</span>
            <select className="select" aria-label="Facility type" value={params.get('facility_type') || ''} onChange={(e) => update({ facility_type: e.target.value })}>
              <option value="">All facility types</option>
              {facilityTypes.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="filter-flags">
            <legend className="field-label">Access</legend>
            {FLAGS.map(([name, label]) => (
              <label key={name} className="check">
                <input type="checkbox" checked={params.get(name) === 'true'} onChange={(e) => update({ [name]: e.target.checked })} />
                <span>{label}</span>
              </label>
            ))}
            <p className="small muted directory-filter-note">Registry matching means a record was matched to a professional register. For inpatient or outpatient care, check the services on the listing and confirm with the facility.</p>
          </fieldset>
          <fieldset className="filter-flags">
            <legend className="field-label">Ratings and feedback</legend>
            {REVIEW_FILTERS.map(([name, label]) => (
              <label key={name} className="check">
                <input type="checkbox" checked={params.get(name) === 'true'} onChange={(event) => update({ [name]: event.target.checked })} />
                <span>{label}</span>
              </label>
            ))}
            <label className="field">
              <span className="field-label">Minimum Google Maps rating</span>
              <select className="select" value={params.get('min_google_rating') || ''} onChange={(event) => update({ min_google_rating: event.target.value })}>
                <option value="">Any rating</option>
                {MINIMUM_GOOGLE_RATINGS.map((rating) => <option key={rating} value={rating}>{rating} and above</option>)}
              </select>
            </label>
            <p className="small muted directory-filter-note">Public feedback here includes published written comments about the facility. Google Maps ratings are separate from ReproCare patient reviews.</p>
          </fieldset>
        </div>
      </details>
      <div className="filters-foot">
        {activeCount > 0 && (
          <button type="button" className="btn btn-ghost" onClick={clearAll}>
            Clear all
          </button>
        )}
        <button type="button" className="btn btn-primary filters-apply" onClick={closeFilters}>
          {resultsPending || results.error ? 'Show results' : `Show ${data?.total ?? 0} ${data?.total === 1 ? 'result' : 'results'}`}
        </button>
      </div>
    </aside>
  );

  const selectedInsurer = insurers.data?.find((i) => i.slug === params.get('insurer'));

  // Active filters as removable chips above the results.
  const chips = [
    params.get('q') && { key: 'q', label: `“${params.get('q')}”` },
    params.get('service') && { key: 'service', label: services.data?.find((x) => x.slug === params.get('service'))?.name || params.get('service') },
    params.get('county') && { key: 'county', label: params.get('county') },
    params.get('town') && { key: 'town', label: params.get('town') },
    point && { key: 'point', label: radius ? `Within ${radius} km of selected point` : 'Distance from selected point', clear: { sort: explicitSort === 'distance' ? '' : explicitSort } },
    params.get('insurer') && { key: 'insurer', label: selectedInsurer?.name || params.get('insurer') },
    params.get('facility_type') && { key: 'facility_type', label: facilityTypes.find((t) => t.value === params.get('facility_type'))?.label || params.get('facility_type') },
    params.get('min_google_rating') && { key: 'min_google_rating', label: `Google Maps ${params.get('min_google_rating')}+` },
    ...[...FLAGS, ...REVIEW_FILTERS].filter(([name]) => params.get(name) === 'true').map(([name, label]) => ({ key: name, label })),
  ].filter(Boolean);

  return (
    <>
      <PageHeader title={text.title} intro={text.intro} crumbs={[{ label: 'Find care', to: '/find-care/facilities' }, { label: text.crumb }]} />
      <div className="container discovery directory-layout">
        {filterPanel}
        {showFilters && <div ref={filterScrim} className="filters-scrim" aria-hidden="true" onClick={closeFilters} />}
        <section className="results" aria-labelledby="results-title">
          <div className="results-toolbar">
            <div>
              <h2 id="results-title" className="results-count" aria-live="polite">
                {resultsPending ? 'Searching…' : data ? `${data.total.toLocaleString()} ${data.total === 1 ? 'facility' : 'facilities'}` : 'Facilities'}
              </h2>
              {point && (
                <p className="small muted">
                  {radius ? `Within ${radius} km of the selected point` : 'No distance limit'}
                  {sort === 'distance' && ' · Nearest first'}
                </p>
              )}
            </div>
            <div className="row">
              <button ref={filterTrigger} className="btn btn-secondary btn-sm filters-open" aria-expanded={showFilters} aria-controls="directory-filters" onClick={() => setShowFilters(true)}>
                <SlidersHorizontal size={16} aria-hidden="true" /> Filters{activeCount ? ` (${activeCount})` : ''}
              </button>
              <label className="sort">
                <span className="sr-only">Sort by</span>
                <select className="select" aria-label="Sort by" value={sort} onChange={(e) => update({ sort: e.target.value })}>
                  {SORTS.map(([name, label]) => <option key={name} value={name}>{label}</option>)}
                  {center && <option value="distance">Distance</option>}
                </select>
              </label>
              <div className="segmented" role="group" aria-label="View">
                <button aria-pressed={view === 'list'} onClick={() => update({ view: 'list' }, { keepPage: true })}>
                  <List size={16} aria-hidden="true" /> List
                </button>
                <button aria-pressed={view === 'grid'} onClick={() => update({ view: 'grid' }, { keepPage: true })}>
                  <Grid2X2 size={16} aria-hidden="true" /> Grid
                </button>
                <button aria-pressed={view === 'map'} onClick={() => update({ view: 'map' }, { keepPage: true })}>
                  <MapIcon size={16} aria-hidden="true" /> Map
                </button>
              </div>
            </div>
          </div>

          {chips.length > 0 && (
            <div className="filter-chips" aria-label="Active filters">
              {chips.map((c) => (
                <button key={c.key} type="button" className="filter-chip" onClick={() => { if (c.key === 'point') clearPoint(); else if (c.key === 'county' || c.key === 'town') cancelLocation(); update(c.clear || { [c.key]: '' }); }} aria-label={`Remove filter: ${c.label}`}>
                  {c.label}
                  <X size={14} aria-hidden="true" />
                </button>
              ))}
              {chips.length > 1 && (
                <button type="button" className="filter-chip-clear" onClick={clearAll}>
                  Clear all
                </button>
              )}
            </div>
          )}

          {(variant === 'insurance' || selectedInsurer) && (
            <Alert tone="info" title={selectedInsurer ? selectedInsurer.name : 'Choose your insurer'}>
              <p>{selectedInsurer ? selectedInsurer.note : 'Pick an insurer in the filters to list facilities that report accepting it.'}</p>
            </Alert>
          )}

          {view === 'map' && (
            <div className="map-panel">
              <MapView points={points} selectedId={selected} onSelect={setSelected} onPick={onPick} center={center} zoom={center ? (!radius || Number(radius) > 25 ? 10 : 12) : 6} fitToPoints={!center} height={variant === 'map' ? 520 : 420} />
              {markers.error ? (
                <ErrorState error={markers.error} onRetry={markers.reload} />
              ) : (
                <p className="small muted map-help">
                  {mapPending ? 'Loading map markers…' : `${points.length} facilities with stored coordinates. Tap the map to choose a search point.`}
                </p>
              )}
            </div>
          )}

          {resultsPending && <LoadingState rows={4} height={170} label="Loading facilities" />}
          {results.error && <ErrorState error={results.error} onRetry={results.reload} />}
          {coveragePending && (
            <LoadingState rows={1} height={90} label="Checking filter coverage" />
          )}
          {data?.total === 0 && !coveragePending && (
            <EmptyState
              title={uncovered.length ? 'This information is not yet recorded in the directory' : 'No facilities match these filters'}
              action={
                <div className="row" style={{ justifyContent: 'center' }}>
                  {uncovered.length > 0 ? (
                    <button className="btn btn-primary" onClick={() => update(Object.fromEntries(uncovered.map((field) => [field, ''])))}>
                      Browse without {uncovered.length === 1 ? 'this filter' : 'these filters'}
                    </button>
                  ) : <button className="btn btn-primary" onClick={clearAll}>Clear filters</button>}
                  <Link className="btn btn-ghost" to="/health-community/programmes">
                    See community programmes
                  </Link>
                </div>
              }
            >
              {uncovered.length ? (
                <>There are no recorded matches for {uncovered.map((field) => field === 'service'
                  ? services.data?.find((item) => item.slug === filters.service)?.name || filters.service
                  : field === 'insurer' ? selectedInsurer?.name || filters.insurer : COVERAGE_LABELS[field]).join(', ')}.
                  Browse the area and ask facilities directly about the care or cover you need.</>
              ) : filters.insurer
                ? 'Try another area or browse without the insurer filter. A facility may accept cover that is not yet recorded in the directory.'
                : 'Try removing a filter or choosing another area.'}
            </EmptyState>
          )}
          {data && data.total > 0 && (
            <>
              <div className={view === "grid" ? "result-list directory-results-grid" : "result-list"}>
                {data.items.map((f) => (
                  <FacilityCard key={f.slug} facility={f} highlightService={params.get('service')} selected={selected === f.slug} onSelect={view === 'map' ? setSelected : undefined} onRequest={setRequesting} />
                ))}
              </div>
              <Pagination showSummary={false}
                page={data.page}
                pages={data.pages}
                total={data.total}
                pageSize={data.page_size}
                noun="facilities"
                onChange={(p) => {
                  update({ page: p });
                  window.scrollTo({ top: 0, behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
                }}
              />
            </>
          )}
          <p className="small muted results-foot">
            Looking for a place not listed here? <Link to="/find-care/google">Search Google Maps live</Link> or <Link to="/contact?topic=listing_correction">tell us about it</Link>.
          </p>
        </section>
      </div>
      {requesting && <AppointmentModal facility={requesting} onClose={() => setRequesting(null)} />}
    </>
  );
}
