import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  CalendarDays,
  HandHeart,
  List,
  Map as MapIcon,
  Search,
} from "lucide-react";
import { api } from "../services/api";
import { townNames } from "../data/townNames";
import { useFetch } from "../hooks/useFetch";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { costTypes, programTypes } from "../data/labels";
import communityPhoto from "../assets/community-care-conversation.webp";
import { PageHeader } from "../components/PageHeader";
import { ProgramCard } from "../components/ProgramCard";
import { MapView } from "../components/MapView";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import "../styles/resource-pages.css";

const title = "Community Programmes & Affordable Care";
const intro =
  "Find screening days, testing, education and outreach. Check the cost, eligibility, organiser and availability before registering.";
const affordable = "free,subsidised";
const filters = [
  "q",
  "town",
  "service",
  "program_type",
  "cost_type",
  "include_past",
];

export default function ProgramsPage({ variant = "all" }) {
  useDocumentTitle(title, intro);
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState("list");
  const services = useFetch(() => api.services(), []);
  const towns = useFetch(() => api.towns(), []);
  const inventory = useFetch(
    (signal) => api.programs({ include_past: true, page_size: 1 }, { signal }),
    [],
  );
  const page = Math.max(1, Number.parseInt(params.get("page"), 10) || 1);
  const query = Object.fromEntries(
    filters.flatMap((key) => (params.get(key) ? [[key, params.get(key)]] : [])),
  );
  const requestedCost = query.cost_type || "";
  const cost =
    variant === "free" &&
    ![affordable, "free", "subsidised"].includes(requestedCost)
      ? affordable
      : requestedCost;
  if (cost) query.cost_type = cost;
  const key = JSON.stringify(query);
  const results = useFetch(
    (signal) => api.programs({ ...query, page, page_size: 15 }, { signal }),
    [key, page],
  );
  const mapData = useFetch(
    (signal) =>
      view === "map"
        ? api.programs({ ...query, page: 1, page_size: 40 }, { signal })
        : null,
    [key, view],
  );

  const update = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) =>
      v ? next.set(k, String(v)) : next.delete(k),
    );
    if (!("page" in changes)) next.delete("page");
    setParams(next);
  };

  const data = results.loading ? null : results.data;
  const points = useMemo(
    () =>
      (mapData.data?.items || [])
        .filter((p) => p.latitude != null && p.longitude != null)
        .map((p) => ({
          id: p.slug,
          name: p.title,
          latitude: p.latitude,
          longitude: p.longitude,
          subtitle: `${p.town} · ${p.start_date}`,
          href: `/programmes/${p.slug}`,
          demo: p.is_demo,
        })),
    [mapData.data],
  );
  const noPublished = inventory.data?.total === 0;
  const hasFilters =
    filters.some((name) => params.has(name)) || variant === "free";

  return (
    <div className="resource-page programme-discovery">
      <PageHeader
        title={title}
        intro={intro}
        crumbs={[
          { label: "Health & community" },
          { label: "Programmes & affordable care" },
        ]}
        tone="green"
        aside={
          <img
            className="header-photo community-header-photo"
            src={communityPhoto}
            width="680"
            height="510"
            alt=""
            loading="lazy"
          />
        }
      />
      <div className="container resource-main">
        <section
          className="resource-filters"
          aria-labelledby="programme-filters"
        >
          <div className="resource-filter-heading">
            <h2 id="programme-filters">Explore programmes</h2>
            {hasFilters && (
              <Link to="/health-community/programmes">Clear filters</Link>
            )}
          </div>
          <form
            className="resource-search"
            role="search"
            onSubmit={(event) => {
              event.preventDefault();
              update({
                q: String(
                  new FormData(event.currentTarget).get("q") || "",
                ).trim(),
              });
            }}
          >
            <label htmlFor="program-q">Programme or organiser</label>
            <div className="resource-search-control">
              <input
                id="program-q"
                name="q"
                className="input"
                key={query.q || ""}
                defaultValue={query.q || ""}
                placeholder="Search by keyword"
                maxLength={100}
              />
              <button className="btn btn-primary">
                <Search size={17} aria-hidden="true" /> Search
              </button>
            </div>
          </form>
          <div className="resource-filter-fields">
            <label>
              Town
              <select
                className="select"
                value={query.town || ""}
                onChange={(event) => update({ town: event.target.value })}
              >
                <option value="">All towns</option>
                {townNames(towns.data || []).map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
            <label>
              Service
              <select
                className="select"
                value={query.service || ""}
                onChange={(event) => update({ service: event.target.value })}
              >
                <option value="">Any service</option>
                {(services.data || []).map((service) => (
                  <option key={service.slug} value={service.slug}>
                    {service.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Programme type
              <select
                className="select"
                value={query.program_type || ""}
                onChange={(event) =>
                  update({ program_type: event.target.value })
                }
              >
                <option value="">All types</option>
                {Object.entries(programTypes).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Cost
              <select
                className="select"
                value={cost}
                onChange={(event) => update({ cost_type: event.target.value })}
              >
                {variant === "all" && <option value="">Any cost</option>}
                <option value={affordable}>Free or subsidised</option>
                {Object.entries(costTypes)
                  .filter(([value]) => variant === "all" || value !== "paid")
                  .map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          {towns.error && (
            <ErrorState error={towns.error} onRetry={towns.reload} />
          )}
          {services.error && (
            <ErrorState error={services.error} onRetry={services.reload} />
          )}
          <label className="check resource-past-filter">
            <input
              type="checkbox"
              checked={query.include_past === "true"}
              onChange={(event) =>
                update({ include_past: event.target.checked })
              }
            />
            Include past events
          </label>
        </section>

        <div className="resource-results-heading">
          <h2 aria-live="polite">
            {results.loading
              ? "Loading programmes…"
              : results.error
                ? "Programmes"
                : `${data?.total ?? 0} ${data?.total === 1 ? "programme" : "programmes"}`}
          </h2>
          <div className="segmented" role="group" aria-label="Programme view">
            <button
              type="button"
              aria-pressed={view === "list"}
              onClick={() => setView("list")}
            >
              <List size={16} aria-hidden="true" /> List
            </button>
            <button
              type="button"
              aria-pressed={view === "map"}
              onClick={() => setView("map")}
            >
              <MapIcon size={16} aria-hidden="true" /> Map
            </button>
          </div>
        </div>

        {view === "map" && (
          <div className="resource-map">
            {mapData.loading && (
              <LoadingState
                rows={1}
                height={180}
                label="Loading programme locations"
              />
            )}
            {mapData.error && (
              <ErrorState error={mapData.error} onRetry={mapData.reload} />
            )}
            {!mapData.loading &&
              !mapData.error &&
              (points.length > 0 ? (
                <>
                  <MapView
                    points={points}
                    height={380}
                    label="Map of programmes"
                  />
                  <p className="small muted map-help">
                    Showing up to 40 matching programmes with a listed location.
                  </p>
                </>
              ) : (
                <p className="muted">
                  No mapped venue locations for these results.
                </p>
              ))}
          </div>
        )}
        {results.loading && <LoadingState rows={3} height={135} />}
        {results.error && (
          <ErrorState error={results.error} onRetry={results.reload} />
        )}
        {data?.total === 0 && (
          <EmptyState
            icon={
              noPublished ? <CalendarDays size={26} /> : <HandHeart size={26} />
            }
            title={
              noPublished
                ? "No programmes are listed yet"
                : hasFilters
                  ? "No programmes match these filters"
                  : query.include_past
                    ? "No programmes are listed"
                    : "No upcoming programmes listed"
            }
            action={
              noPublished ? (
                <div className="row">
                  <Link className="btn btn-primary" to="/find-care/facilities">
                    Find care instead
                  </Link>
                  <Link to="/health-community/alerts">
                    Check public health updates
                  </Link>
                </div>
              ) : hasFilters ? (
                <Link
                  className="btn btn-secondary"
                  to="/health-community/programmes"
                >
                  Clear filters
                </Link>
              ) : (
                <button
                  className="btn btn-secondary"
                  onClick={() => update({ include_past: true })}
                >
                  Include past events
                </button>
              )
            }
          >
            {noPublished
              ? "Check back for listings or contact a facility directly to ask about upcoming outreach and reduced-cost services."
              : "Check another town, service or cost option."}
          </EmptyState>
        )}
        {data?.total > 0 && (
          <>
            <div className="program-list">
              {data.items.map((program) => (
                <ProgramCard key={program.slug} program={program} />
              ))}
            </div>
            <Pagination
              showSummary={false}
              page={data.page}
              pages={data.pages}
              total={data.total}
              pageSize={data.page_size}
              noun="programmes"
              onChange={(next) => update({ page: next })}
            />
          </>
        )}
      </div>
    </div>
  );
}
