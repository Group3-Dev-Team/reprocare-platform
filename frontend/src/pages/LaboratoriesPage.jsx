import { facilityDisplayName } from '../data/facilityNames';
import { Link, useSearchParams } from 'react-router-dom';
import { Home } from 'lucide-react';
import { api } from '../services/api';
import { townNames } from '../data/townNames';
import { useFetch } from '../hooks/useFetch';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import { PageHeader } from '../components/PageHeader';
import { FacilityCard } from '../components/FacilityCard';
import { Pagination } from '../components/Pagination';
import { DemoLabel } from '../components/Badges';
import { EmptyState, ErrorState, LoadingState } from '../components/Feedback';

/** Two ways in: search by test name, or browse laboratories. */
export default function LaboratoriesPage() {
  useDocumentTitle('Laboratories & tests', 'Find diagnostic laboratories and reproductive health tests in Kenya, with turnaround times, prices and home collection.');
  const [params, setParams] = useSearchParams();
  const q = params.get('q') || '';
  const town = params.get('town') || '';
  const home = params.get('home_collection') === 'true';
  const testPage = Number(params.get('tests_page') || 1);
  const labPage = Number(params.get('page') || 1);
  const towns = useFetch(() => api.towns(), []);
  const tests = useFetch((signal) => api.labTests({ q, town, home_collection: home, page: testPage, page_size: 15 }, { signal }), [q, town, home, testPage]);
  const labs = useFetch((signal) => api.facilities({ facility_type: 'laboratory', town, page: labPage, page_size: 15 }, { signal }), [town, labPage]);

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, String(v)) : next.delete(k)));
    if ('town' in changes) next.delete('page');
    if ('town' in changes || 'q' in changes || 'home_collection' in changes) next.delete('tests_page');
    setParams(next);
  };

  return (
    <>
      <PageHeader
        title="Laboratories & tests"
        intro="Search for a test to see which laboratories list it, how long results take and whether samples can be collected at home. Prices are stated by laboratories and can change."
        crumbs={[{ label: 'Find care', to: '/find-care/facilities' }, { label: 'Laboratories' }]}
      >
        <form className="inline-search" role="search" onSubmit={(e) => {
          e.preventDefault();
          update({ q: new FormData(e.currentTarget).get('q').trim() });
          document.getElementById('lab-test-results')?.scrollIntoView();
        }}>
          <label className="sr-only" htmlFor="test-q">Search tests</label>
          <input id="test-q" name="q" className="input" defaultValue={q} key={q} maxLength={100} placeholder="e.g. HIV, pregnancy test, hormone panel" />
          <button className="btn btn-primary">Search tests</button>
        </form>
      </PageHeader>

      <div className="container section-sm directory-reference">
        <div className="filter-row directory-reference-filters">
          <select className="select" aria-label="Town" value={town} onChange={(e) => update({ town: e.target.value })}>
            <option value="">All towns</option>
            {townNames(towns.data || []).map((name) => <option key={name}>{name}</option>)}
          </select>
        </div>

        <section aria-labelledby="labs-title" className="section-sm">
          <h2 id="labs-title">Laboratories {town && `in ${town}`}</h2>
          {!labs.loading && labs.data?.total > 0 && <p className="small muted">{labs.data.total.toLocaleString()} {labs.data.total === 1 ? 'listing' : 'listings'}</p>}
          {labs.loading && <LoadingState rows={2} height={160} />}
          {labs.error && <ErrorState error={labs.error} onRetry={labs.reload} />}
          {!labs.loading && labs.data?.total === 0 && <EmptyState title={town ? `No laboratories listed in ${town}` : 'No laboratories listed yet'} action={town ? <button className="btn btn-secondary" onClick={() => update({ town: '' })}>Show all towns</button> : undefined} />}
          {!labs.loading && labs.data?.total > 0 && (
            <>
              <div className="result-list">
                {labs.data.items.map((f) => (
                  <FacilityCard key={f.slug} facility={f} />
                ))}
              </div>
              <Pagination page={labs.data.page} pages={labs.data.pages} total={labs.data.total} pageSize={labs.data.page_size} noun="laboratories" onChange={(p) => update({ page: p })} />
            </>
          )}
        </section>
        <section aria-labelledby="tests-title" className="section-sm" id="lab-test-results">
          <h2 id="tests-title">{q ? `Tests matching “${q}”` : 'Tests listed by laboratories'}</h2>
          <label className="check">
            <input type="checkbox" checked={home} onChange={(e) => update({ home_collection: e.target.checked })} />
            <span>Home sample collection</span>
          </label>
          {tests.loading && <LoadingState rows={1} height={240} />}
          {tests.error && <ErrorState error={tests.error} onRetry={tests.reload} />}
          {!tests.loading && tests.data?.total === 0 && (
            <EmptyState title={q || town || home ? 'No recorded test matches' : 'Test menus are not listed yet'}>
              Use the laboratory listings above to contact a provider about available tests and sample collection.
            </EmptyState>
          )}
          {!tests.loading && tests.data?.total > 0 && (
            <>
              <div className="table-wrap lab-results-table">
                <table className="table table-stack">
                  <thead>
                    <tr>
                      <th>Test</th>
                      <th>Laboratory</th>
                      <th>Sample</th>
                      <th>Results in</th>
                      <th>Price (stated)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tests.data.items.map((t) => (
                      <tr key={t.id}>
                        <td data-label="Test">
                          <strong>{t.name}</strong>
                          {t.home_collection && (
                            <span className="badge badge-success" style={{ marginLeft: 8 }}>
                              <Home size={12} aria-hidden="true" /> Home collection
                            </span>
                          )}
                        </td>
                        <td data-label="Laboratory">
                          <Link to={`/facilities/${t.facility.slug}`}>{facilityDisplayName(t.facility)}</Link>
                          <div className="small muted">{t.facility.town}</div>
                          {t.facility.is_demo && <DemoLabel />}
                        </td>
                        <td data-label="Sample">{t.sample_type}</td>
                        <td data-label="Results in">{t.turnaround}</td>
                        <td data-label="Price (stated)">{t.price_note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={tests.data.page} pages={tests.data.pages} total={tests.data.total} pageSize={tests.data.page_size} noun="tests" onChange={(p) => update({ tests_page: p })} />
            </>
          )}
        </section>

      </div>
    </>
  );
}
