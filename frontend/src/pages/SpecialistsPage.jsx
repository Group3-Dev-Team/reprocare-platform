import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { townNames } from '../data/townNames';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/PageHeader';
import { PractitionerCard } from '../components/PractitionerCard';
import { Pagination } from '../components/Pagination';
import { EmptyState, ErrorState, LoadingState } from '../components/Feedback';

export default function SpecialistsPage() {
  useDocumentTitle('Specialists & practitioners', 'Find obstetricians, midwives, fertility specialists, counsellors and other reproductive health practitioners in Kenya.');
  const [params, setParams] = useSearchParams();
  const specialties = useFetch(() => api.specialties(), []);
  const towns = useFetch(() => api.towns(), []);
  const key = params.toString();
  const requestedPage = Number(params.get('page') || 1);
  const page = Number.isSafeInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const results = useFetch((signal) => api.practitioners({ ...Object.fromEntries(params.entries()), page, page_size: 15 }, { signal }), [key]);

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, String(v)) : next.delete(k)));
    if (!('page' in changes)) next.delete('page');
    setParams(next);
  };
  const data = results.loading ? null : results.data;
  const filtered = ['q', 'specialty', 'town', 'gender', 'telehealth', 'verified_only'].some((field) => params.has(field));
  // Without filters, the results total tells us whether the directory has entries. With filters, the specialty
  // list (one entry per listed specialty) does — but only once it has loaded successfully.
  const directoryKnown = !filtered || (!specialties.loading && !specialties.error && Array.isArray(specialties.data));
  const directoryEmpty = filtered ? directoryKnown && specialties.data.length === 0 : data?.total === 0;
  const mismatched = filtered && directoryKnown && !directoryEmpty;
  const referenceFailed = specialties.error || towns.error;

  return (
    <>
      <PageHeader
        title="Specialists & practitioners"
        intro="Doctors, midwives, nurses, sonographers and counsellors working in reproductive health. Where a professional register has been checked, the listing says which one and when."
        crumbs={[{ label: 'Find care', to: '/find-care/facilities' }, { label: 'Specialists' }]}
      >
        <form
          className="inline-search"
          role="search"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: new FormData(e.currentTarget).get('q').trim() });
          }}
        >
          <label className="sr-only" htmlFor="practitioner-q">
            Search practitioners
          </label>
          <input id="practitioner-q" name="q" className="input" defaultValue={params.get('q') || ''} key={params.get('q')} maxLength={100} placeholder="Name, specialty or town" />
          <button className="btn btn-primary">Search</button>
        </form>
      </PageHeader>
      <div className="container section-sm directory-reference">
        <div className="filter-row directory-reference-filters">
          <select className="select" aria-label="Specialty" value={params.get('specialty') || ''} onChange={(e) => update({ specialty: e.target.value })}>
            <option value="">All specialties</option>
            {(specialties.data || []).map((s) => (
              <option key={s.name} value={s.name}>
                {s.name} ({s.count})
              </option>
            ))}
          </select>
          <select className="select" aria-label="Town" value={params.get('town') || ''} onChange={(e) => update({ town: e.target.value })}>
            <option value="">All towns</option>
            {townNames(towns.data || []).map((name) => <option key={name}>{name}</option>)}
          </select>
          <select className="select" aria-label="Gender" value={params.get('gender') || ''} onChange={(e) => update({ gender: e.target.value })}>
            <option value="">Any gender</option>
            <option value="female">Female practitioner</option>
            <option value="male">Male practitioner</option>
          </select>
          <label className="check">
            <input type="checkbox" checked={params.get('telehealth') === 'true'} onChange={(e) => update({ telehealth: e.target.checked })} />
            <span>Telehealth</span>
          </label>
          <label className="check">
            <input type="checkbox" checked={params.get('verified_only') === 'true'} onChange={(e) => update({ verified_only: e.target.checked })} />
            <span>Register checked</span>
          </label>
        </div>
        {referenceFailed && (
          <p className="small muted" role="status">
            Some filter options could not be loaded.{' '}
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => { if (specialties.error) specialties.reload(); if (towns.error) towns.reload(); }}>Try again</button>
          </p>
        )}
        <h2 className="results-count" aria-live="polite">
          {results.loading ? 'Searching…' : data ? `${data.total.toLocaleString()} ${data.total === 1 ? 'practitioner' : 'practitioners'}` : 'Practitioners'}
        </h2>
        {results.loading && <LoadingState rows={3} height={140} />}
        {results.error && <ErrorState error={results.error} onRetry={results.reload} />}
        {data?.total === 0 && filtered && !directoryKnown && specialties.loading && <LoadingState rows={1} height={90} />}
        {data?.total === 0 && filtered && !directoryKnown && !specialties.loading && (
          <EmptyState
            title="No practitioner listings found for these filters"
            action={<button className="btn btn-primary" onClick={() => setParams(new URLSearchParams())}>Clear filters</button>}
          >
            Clear the filters to see every listed practitioner.
          </EmptyState>
        )}
        {data?.total === 0 && directoryKnown && (
          <EmptyState
            title={mismatched ? 'No practitioner listings match these filters' : 'Practitioner profiles are not listed yet'}
            action={mismatched ? <button className="btn btn-primary" onClick={() => setParams(new URLSearchParams())}>Clear filters</button>
              : <Link className="btn btn-primary" to="/find-care/facilities">Browse facilities</Link>}
          >
            {mismatched ? 'Try another specialty or town.' : (
              <>Contact a facility to ask which specialists are available. You can look up doctors and dentists in the <a href="https://registers.kmpdc.go.ke/" target="_blank" rel="noreferrer">KMPDC register</a>.</>
            )}
          </EmptyState>
        )}
        {data?.total > 0 && (
          <>
            <div className="card-grid">
              {data.items.map((p) => (
                <PractitionerCard key={p.slug} practitioner={p} />
              ))}
            </div>
            <Pagination showSummary={false} page={data.page} pages={data.pages} total={data.total} pageSize={data.page_size} noun="practitioners" onChange={(p) => update({ page: p })} />
          </>
        )}
      </div>
    </>
  );
}
