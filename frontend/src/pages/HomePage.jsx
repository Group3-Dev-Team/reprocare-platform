HEAD;
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BookOpen,
  Bot,
  Building2,
  CalendarCheck,
  ClipboardList,
  GitCompareArrows,
  MapPin,
  Search,
  ShieldCheck,
  Stethoscope,
} from "lucide-react";
import { api } from "../services/api";
import { useFetch } from "../hooks/useFetch";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { facilityTypes } from "../data/labels";
import { serviceIcons } from "../data/serviceIcons";
import { ProgramCard } from "../components/ProgramCard";
import { ErrorState, LoadingState } from "../components/Feedback";
import clinician from "../assets/reprocare-clinician-hero.webp";
import clinicianSmall from "../assets/reprocare-clinician-hero-small.webp";
import familyArt from "../assets/reprocare-family-hero.webp";
import familyArtSmall from "../assets/reprocare-family-visit-small.webp";

const nextSteps = [
  {
    to: "/find-care/facilities",
    label: "Find care",
    icon: Search,
    tone: "blue",
    description:
      "Browse healthcare facilities by location and the details they report.",
  },
  {
    to: "/compare",
    label: "Care Decision Assistant",
    icon: GitCompareArrows,
    tone: "mint",
    description:
      "Choose a care goal, then weigh up services, hours, feedback and cover for up to three facilities.",
  },
  {
    to: "/prepare-for-your-visit",
    label: "Prepare for your visit",
    icon: ClipboardList,
    tone: "violet",
    description: "Make a private checklist of the questions you want to ask.",
  },
];
const sources = [
  [
    "Official registration",
    "A matched record shows the registry and the date it was checked.",
  ],
  [
    "Facility information",
    "Services, hours and accepted insurers come from facility listings. Confirm details before travelling.",
  ],
  ["Patient reviews", "Moderated experiences submitted directly to ReproCare."],
  [
    "Public feedback",
    "Comments from public sources appear separately, with links to the original posts.",
  ],
];

export default function HomePage() {
  useDocumentTitle(
    null,
    "Find reproductive healthcare in Kenya. Search by service and county, compare facilities, and see where listing information comes from.",
  );
  const services = useFetch(() => api.services(), []);
  const counties = useFetch(() => api.counties(), []);
  const insurers = useFetch(() => api.insurers(), []);
  const programs = useFetch(() => api.programs({ page_size: 3 }), []);
  const articles = useFetch(() => api.articles(), []);
  const stats = useFetch(() => api.stats(), []);
  const [service, setService] = useState("");
  const [county, setCounty] = useState("");
  const [facilityType, setFacilityType] = useState("");
  const [insurer, setInsurer] = useState("");
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const search = (event) => {
    event.preventDefault();
    const params = new URLSearchParams();
    if (service) params.set("service", service);
    if (county) params.set("county", county);
    if (facilityType) params.set("facility_type", facilityType);
    if (insurer) params.set("insurer", insurer);
    if (query.trim()) params.set("q", query.trim());
    navigate(`/find-care/facilities${params.size ? `?${params}` : ""}`);
  };

  return (
    <div className="home-v2">
      <section className="home-hero">
        <div className="container home-hero-layout">
          <div className="home-hero-copy">
            <p className="home-hero-eyebrow">
              <BadgeCheck size={16} aria-hidden="true" /> Independent
              reproductive healthcare directory for Kenya
            </p>
            <h1>
              Find reproductive care <span>in Kenya.</span>
            </h1>
            <p className="lede">
              Search by service or location, see where listing details come from
              and make a plan for your next healthcare visit.
            </p>
            <div className="home-hero-links">
              <Link to="/how-it-works">
                How ReproCare works <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </div>
          </div>

          <form
            id="home-find-care"
            className="home-search"
            onSubmit={search}
            role="search"
            aria-label="Find care"
          >
            <div className="home-search-fields">
              <div className="field">
                <label className="field-label" htmlFor="home-filter-service">
                  <Stethoscope size={15} aria-hidden="true" /> Service
                </label>
                <select
                  id="home-filter-service"
                  className="select"
                  value={service}
                  onChange={(event) => setService(event.target.value)}
                >
                  <option value="">Any service</option>
                  {(services.data || []).map((item) => (
                    <option key={item.slug} value={item.slug}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label className="field-label" htmlFor="home-filter-county">
                  <MapPin size={15} aria-hidden="true" /> County
                </label>
                <select
                  id="home-filter-county"
                  className="select"
                  value={county}
                  onChange={(event) => setCounty(event.target.value)}
                >
                  <option value="">Any county</option>
                  {(counties.data || []).map((item) => (
                    <option key={item.county} value={item.county}>
                      {item.county}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label
                  className="field-label"
                  htmlFor="home-filter-facility-type"
                >
                  <Building2 size={15} aria-hidden="true" /> Facility type
                </label>
                <select
                  id="home-filter-facility-type"
                  className="select"
                  value={facilityType}
                  onChange={(event) => setFacilityType(event.target.value)}
                >
                  <option value="">All facility types</option>
                  {facilityTypes.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
              <button className="btn btn-primary btn-lg" type="submit">
                <Search size={19} aria-hidden="true" /> Find care
              </button>
            </div>
            <details>
              <summary>More filters</summary>
              <div className="home-search-extra">
                <div>
                  <div className="field">
                    <label
                      className="field-label"
                      htmlFor="home-filter-insurer"
                    >
                      Insurer
                    </label>
                    <select
                      id="home-filter-insurer"
                      className="select"
                      value={insurer}
                      onChange={(event) => setInsurer(event.target.value)}
                      aria-describedby="home-insurer-coverage"
                    >
                      <option value="">All insurers</option>
                      {(insurers.data || []).map((item) => (
                        <option key={item.slug} value={item.slug}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <p id="home-insurer-coverage" className="small muted">
                    This filter uses reported cover. Some listings have no
                    insurer information.
                  </p>
                </div>
                <div className="field">
                  <label className="field-label" htmlFor="home-filter-query">
                    Facility name or area
                  </label>
                  <input
                    id="home-filter-query"
                    className="input"
                    type="search"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    maxLength={100}
                  />
                </div>
              </div>
            </details>
            {(services.error || counties.error || insurers.error) && (
              <p role="status" className="small muted">
                Some search options could not load. You can still browse the
                directory.
              </p>
            )}
          </form>

          <figure className="home-hero-art">
            <img
              src={clinician}
              srcSet={clinicianSmall + " 640w, " + clinician + " 1200w"}
              sizes="(max-width: 760px) calc(100vw - 40px), (max-width: 1240px) 45vw, 560px"
              alt="Kenyan healthcare professional in a consultation room"
              width="1200"
              height="960"
              fetchpriority="high"
            />
            {stats.data?.facilities > 0 && (
              <figcaption className="home-hero-chip home-hero-chip-count">
                <Building2 size={18} aria-hidden="true" />
                <span>
                  <strong>{stats.data.facilities.toLocaleString()}</strong>{" "}
                  facilities listed
                  {stats.data.towns ? ` in ${stats.data.towns} towns` : ""}
                </span>
              </figcaption>
            )}
            <span
              className="home-hero-chip home-hero-chip-source"
              aria-hidden="true"
            >
              <ShieldCheck size={18} /> Sources shown on every listing
            </span>
          </figure>
        </div>
      </section>

      <section
        className="section container home-actions"
        aria-labelledby="home-next-step"
      >
        <h2 id="home-next-step">Plan your next step</h2>
        <ul className="home-task-list">
          {nextSteps.map(({ to, label, description, icon: Icon, tone }) => (
            <li key={to}>
              <Link className={"home-task home-task-" + tone} to={to}>
                <span className="home-task-icon">
                  <Icon size={22} aria-hidden="true" />
                </span>
                <strong>{label}</strong>
                <span className="home-task-description">{description}</span>
                <ArrowUpRight
                  className="home-task-arrow"
                  size={19}
                  aria-hidden="true"
                />
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="section container home-services">
        <div className="section-head">
          <h2>Explore care by service</h2>
        </div>
        {services.loading && <LoadingState rows={2} height={58} />}
        {services.error && (
          <ErrorState error={services.error} onRetry={services.reload} />
        )}
        <ul>
          {(services.data || []).map((item) => {
            const Icon = serviceIcons[item.slug] || Search;
            return (
              <li key={item.slug}>
                <Link
                  to={`/find-care/facilities?service=${encodeURIComponent(item.slug)}`}
                >
                  <Icon size={22} aria-hidden="true" />
                  <span>
                    <strong>{item.name}</strong>
                    <small>{item.short_description}</small>
                  </span>
                  <ArrowUpRight size={17} aria-hidden="true" />
                </Link>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="home-source-band section">
        <div className="container home-editorial">
          <div>
            <ShieldCheck size={27} aria-hidden="true" />
            <h2>Know where each listing detail comes from.</h2>
            <Link to="/trust" className="btn btn-secondary">
              Our approach to trust <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <dl>
            {sources.map(([name, description]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{description}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section
        className="section container home-preparation"
        aria-labelledby="home-prepare-heading"
      >
        <div className="home-preparation-inner">
          <div className="home-preparation-copy">
            <h2 id="home-prepare-heading">
              Bring your questions to the visit.
            </h2>
            <p>
              Use the checklist to write down what you would like to ask, check
              what to bring and print a copy if you want one.
            </p>
            <Link className="btn btn-primary" to="/prepare-for-your-visit">
              Prepare for your visit <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <img
            src={familyArt}
            srcSet={familyArtSmall + " 640w, " + familyArt + " 1448w"}
            sizes="(max-width: 530px) calc(100vw - 42px), (max-width: 1280px) 42vw, 550px"
            alt="Illustration of a pregnant woman with her partner and child"
            width="1448"
            height="1086"
            loading="lazy"
            decoding="async"
          />
        </div>
      </section>

      <section className="section container home-guides">
        <div className="section-head spread">
          <div>
            <h2>Understand your care options</h2>
            <p>
              Read our health guides or find general answers in the Health
              Assistant.
            </p>
          </div>
          <Link className="btn btn-secondary" to="/health-library">
            Health Library <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
        <div className="home-guide-grid">
          <div className="home-guide-list">
            {articles.loading && <LoadingState rows={2} height={48} />}
            {articles.error && (
              <ErrorState error={articles.error} onRetry={articles.reload} />
            )}
            <ul className="article-links">
              {(articles.data || []).slice(0, 4).map((article) => (
                <li key={article.slug}>
                  <Link to={`/health-library/${article.slug}`}>
                    <BookOpen size={17} aria-hidden="true" />
                    <span>{article.title}</span>
                    <small>{article.read_minutes} min read</small>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className="home-guide-assistant">
            <Bot size={24} aria-hidden="true" />
            <h3>Have a general question?</h3>
            <p>
              Explore reviewed guides in English or Kiswahili with the Health
              Assistant.
            </p>
            <Link to="/assistant" className="btn btn-secondary">
              Open the assistant <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </section>

      <section className="section home-community">
        <div className="container">
          <div className="section-head spread">
            <div>
              <h2>Community Programmes &amp; Affordable Care</h2>
              <p>
                Browse community initiatives, screening events and subsidised
                care where listings are available.
              </p>
            </div>
            <Link to="/health-community/programmes" className="btn btn-primary">
              <CalendarCheck size={17} aria-hidden="true" /> Browse programmes
            </Link>
          </div>
          {!!programs.data?.items?.length && (
            <div className="program-list">
              {programs.data.items.map((program) => (
                <ProgramCard key={program.slug} program={program} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
