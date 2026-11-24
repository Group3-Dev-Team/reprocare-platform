import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowDownRight,
  ArrowUpRight,
  BookOpen,
  Clock,
  Search,
} from "lucide-react";
import { readCarePlan, writeCarePlan } from "../data/careplan";
import { api } from "../services/api";
import { formatDate } from "../data/labels";
import { useFetch } from "../hooks/useFetch";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import consultation from "../assets/about-care-conversation.webp";
import consultationSmall from "../assets/about-care-conversation-small.webp";
import { HealthFaq } from "../components/HealthFaq";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "../components/Feedback";
import "../styles/resource-pages.css";

function GuideCard({ guide, featured = false, saved, onToggle }) {
  return (
    <article
      className={`library-entry${featured ? " library-entry-featured" : ""}`}
    >
      {featured && (
        <div className="library-cover" aria-hidden="true">
          <img
            src={consultationSmall}
            srcSet={`${consultationSmall} 560w, ${consultation} 1000w`}
            sizes="(max-width: 760px) 100vw, 340px"
            alt=""
            width="560"
            height="420"
            loading="lazy"
          />
        </div>
      )}
      <div className="library-entry-body">
        <p className="article-category">{guide.category}</p>
        <h3>
          <Link to={`/health-library/${guide.slug}`}>
            {guide.title} <ArrowUpRight size={17} aria-hidden="true" />
          </Link>
        </h3>
        <p>{guide.summary}</p>
        <span className="small muted row">
          <Clock size={15} aria-hidden="true" /> {guide.read_minutes} min read
          {guide.updated_on && <> · Updated {formatDate(guide.updated_on)}</>}
        </span>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          aria-pressed={saved}
          aria-label={`Save ${guide.title} to reading list`}
          onClick={onToggle}
        >
          {saved ? "Saved to reading list" : "Save to reading list"}
        </button>
      </div>
    </article>
  );
}

export default function LibraryPage() {
  useDocumentTitle(
    "Health library",
    "Plain-language guides on reproductive healthcare in Kenya.",
  );
  const [faqLanguage, setFaqLanguage] = useState("en");
  const [plan, setPlan] = useState(readCarePlan);
  const [storageError, setStorageError] = useState(false);
  const toggleGuide = (slug) => {
    const guides = plan.guides.includes(slug)
      ? plan.guides.filter((item) => item !== slug)
      : [...plan.guides, slug];
    const next = { ...plan, guides };
    setStorageError(!writeCarePlan(next));
    setPlan(next);
  };
  const cardProps = (guide) => ({
    guide,
    saved: plan.guides.includes(guide.slug),
    onToggle: () => toggleGuide(guide.slug),
  });
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const category = params.get("category") || "";
  const all = useFetch((signal) => api.articles(undefined, { signal }), []);
  const results = useFetch(
    (signal) =>
      q || category
        ? api.articles({ q, category }, { signal })
        : Promise.resolve(null),
    [q, category],
  );
  const filtered = Boolean(q || category);
  const view = filtered ? results : all;
  const categories = [
    ...new Set((all.data || []).map((guide) => guide.category)),
  ].sort();
  const guides = view.loading ? [] : view.data || [];
  const featured = filtered
    ? null
    : guides.find((guide) => guide.slug === "contraception-options") ||
      guides[0];
  const remaining = guides.filter((guide) => guide.slug !== featured?.slug);
  const set = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };

  return (
    <div className="resource-page resource-library">
      <PageHeader
        title="Health library"
        intro="Understand your options and prepare for your next visit. Explore plain-language guides with references you can check."
        crumbs={[
          { label: "Health & community", to: "/health-community/programmes" },
          { label: "Health library" },
        ]}
      >
        <form
          className="resource-search library-search"
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            set(
              "q",
              String(new FormData(event.currentTarget).get("q") || "").trim(),
            );
          }}
        >
          <label className="sr-only" htmlFor="lib-q">
            Search the library
          </label>
          <div className="resource-search-control">
            <input
              id="lib-q"
              name="q"
              className="input"
              key={q}
              defaultValue={q}
              maxLength={100}
              placeholder="e.g. screening or contraception"
            />
            <button className="btn btn-primary">
              <Search size={17} aria-hidden="true" /> Search
            </button>
          </div>
        </form>
      </PageHeader>
      <div className="container resource-main library-layout">
        <aside className="library-topics">
          <h2>Browse by topic</h2>
          <p className="small muted">
            Saving a guide keeps it in this tab’s reading list.
          </p>
          <Link to="/care-planner">
            Open care planner
            {plan.guides.length ? ` · ${plan.guides.length} saved` : ""}
          </Link>
          {storageError && (
            <p className="small muted" role="status">
              Browser storage is unavailable. Saves cannot carry over to the
              care planner.
            </p>
          )}
          {all.loading && (
            <LoadingState rows={2} height={35} label="Loading topics" />
          )}
          {all.error && filtered && (
            <ErrorState error={all.error} onRetry={all.reload} />
          )}
          <div className="library-topic-list" role="group" aria-label="Topics">
            <button
              type="button"
              aria-pressed={!category}
              onClick={() => set("category", "")}
            >
              All topics <ArrowDownRight size={15} aria-hidden="true" />
            </button>
            {categories.map((topic) => (
              <button
                key={topic}
                type="button"
                aria-pressed={category === topic}
                onClick={() => set("category", topic)}
              >
                {topic}
              </button>
            ))}
          </div>
        </aside>
        <section aria-labelledby="library-results">
          <div className="resource-results-heading">
            <h2 id="library-results">
              {category || (q ? "Search results" : "Explore the guides")}
            </h2>
            {filtered && (
              <Link to="/health-library">Clear search and topic</Link>
            )}
          </div>
          {view.loading && <LoadingState rows={2} height={160} />}
          {view.error && (
            <ErrorState error={view.error} onRetry={view.reload} />
          )}
          {!view.loading && !view.error && !guides.length && (
            <EmptyState
              icon={<BookOpen size={26} />}
              title={
                filtered
                  ? "No guides match that search"
                  : "No guides are available yet"
              }
              action={
                <Link className="btn btn-secondary" to="/assistant">
                  Ask the health assistant
                </Link>
              }
            >
              {filtered && "Try a shorter search or choose another topic."}
            </EmptyState>
          )}
          {featured && <GuideCard {...cardProps(featured)} featured />}
          {remaining.length > 0 && (
            <div className="library-grid">
              {remaining.map((guide) => (
                <GuideCard key={guide.slug} {...cardProps(guide)} />
              ))}
            </div>
          )}
          <section
            className="assistant-faq"
            aria-labelledby="library-faq"
            lang={faqLanguage}
          >
            <div className="resource-results-heading">
              <h2 id="library-faq">
                {faqLanguage === "sw"
                  ? "Maswali yanayoulizwa mara kwa mara"
                  : "Frequently asked questions"}
              </h2>
              <div
                className="segmented"
                role="group"
                aria-label={
                  faqLanguage === "sw" ? "Lugha ya maswali" : "FAQ language"
                }
              >
                <button
                  type="button"
                  lang="en"
                  aria-pressed={faqLanguage === "en"}
                  onClick={() => setFaqLanguage("en")}
                >
                  English
                </button>
                <button
                  type="button"
                  lang="sw"
                  aria-pressed={faqLanguage === "sw"}
                  onClick={() => setFaqLanguage("sw")}
                >
                  Kiswahili
                </button>
              </div>
            </div>
            <HealthFaq lang={faqLanguage} />
          </section>
          <section className="panel stack" aria-labelledby="other-reading">
            <h2 id="other-reading">Official updates and learning resources</h2>
            <p>
              <Link to="/health-community/alerts">
                Public health updates for Kenya
              </Link>
            </p>
            <p>
              <Link to="/assistant">
                Educational questions in English or Kiswahili
              </Link>
            </p>
            <p>
              <a href="https://www.who.int/initiatives/epi-win/epi-win-webinars">
                WHO public health webinars and recordings
              </a>
            </p>
          </section>
        </section>
      </div>
    </div>
  );
}
