import { useEffect } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ArrowUpRight, BookOpen, Clock, Search } from "lucide-react";
import { api } from "../services/api";
import { useFetch } from "../hooks/useFetch";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDate } from "../data/labels";
import { Breadcrumbs } from "../components/PageHeader";
import { ErrorState, LoadingState } from "../components/Feedback";
import NotFoundPage from "./NotFoundPage";
import "../styles/resource-pages.css";

const whoSources = {
  "WHO recommendations on antenatal care for a positive pregnancy experience (2016)":
    "https://www.who.int/publications/b/31382",
  "Guidelines for the management of symptomatic sexually transmitted infections (2021)":
    "https://www.who.int/publications/b/57829",
  "Medical eligibility criteria for contraceptive use":
    "https://www.who.int/publications/i/item/9789240115583",
  "Infertility: key facts and guidance":
    "https://www.who.int/news-room/fact-sheets/detail/infertility",
  "Guideline for screening and treatment of cervical pre-cancer lesions":
    "https://www.who.int/publications-detail-redirect/9789240030824",
  "Emergency contraception fact sheet":
    "https://www.who.int/en/news-room/fact-sheets/detail/emergency-contraception",
  "WHO recommendations on maternal and newborn care for a positive postnatal experience (2022)":
    "https://www.who.int/publications/i/item/9789240045989",
};

export default function ArticlePage() {
  const { slug } = useParams();
  return <ArticleReader key={slug} slug={slug} />;
}

function ArticleReader({ slug }) {
  const result = useFetch((signal) => api.article(slug, { signal }), [slug]);
  const services = useFetch(() => api.services(), []);
  const all = useFetch(() => api.articles(), []);
  const article = result.data;
  const { hash, key: locationKey } = useLocation();
  useEffect(() => {
    if (article && hash)
      document
        .getElementById(hash.slice(1))
        ?.scrollIntoView({ block: "start" });
  }, [article, hash, locationKey]);
  const notFound = result.error?.status === 404;
  useDocumentTitle(
    notFound ? "Not found" : article?.title,
    notFound ? "ReproCare could not find this page." : article?.summary,
    {
      type: article ? "article" : "website",
      modifiedTime: article?.updated_on,
      noIndex: !article,
    },
  );

  if (notFound) return <NotFoundPage what="article" />;
  if (result.error)
    return (
      <div className="container section">
        <ErrorState error={result.error} onRetry={result.reload} />
      </div>
    );
  if (!article)
    return (
      <div className="container section">
        <LoadingState rows={3} />
      </div>
    );

  const serviceIds = article.related_services || [];
  const related = (all.data || [])
    .filter(
      (item) =>
        item.slug !== article.slug &&
        (item.category === article.category ||
          item.related_services?.some((service) =>
            serviceIds.includes(service),
          )),
    )
    .slice(0, 3);
  const serviceNames = (services.data || []).filter((service) =>
    serviceIds.includes(service.slug),
  );
  const sections = article.sections || [];
  const questions = article.questions_to_ask || [];
  const references = article.references || [];

  return (
    <div className="resource-page resource-reader">
      <header className="reader-header">
        <div className="container">
          <Breadcrumbs
            items={[
              { label: "Health library", to: "/health-library" },
              { label: article.title },
            ]}
          />
          <div className="reader-intro">
            <p className="article-category">{article.category}</p>
            <h1>{article.title}</h1>
            <p className="lede">{article.summary}</p>
            <div className="reader-meta small">
              <span>
                <Clock size={16} aria-hidden="true" /> {article.read_minutes}{" "}
                min read
              </span>
              {article.updated_on && (
                <span>Updated {formatDate(article.updated_on)}</span>
              )}
              {references.length > 0 && (
                <Link to="#guide-sources">Read the sources</Link>
              )}
            </div>
          </div>
        </div>
      </header>
      <div className="container reader-layout">
        <article className="article reader-copy">
          <div className="reader-note">
            <BookOpen size={21} aria-hidden="true" />
            <div>
              <p>
                This guide provides general information. For advice about your
                own health, speak with a qualified health worker.
              </p>
              {article.review_status && (
                <p className="small muted">{article.review_status}</p>
              )}
            </div>
          </div>
          {sections.map((section, index) => (
            <section
              className="reader-section"
              key={section.heading}
              id={`guide-section-${index + 1}`}
            >
              <h2>{section.heading}</h2>
              {(section.paragraphs || []).map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              {section.list?.length > 0 && (
                <ul>
                  {section.list.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
            </section>
          ))}
          {questions.length > 0 && (
            <section
              className="questions-box reader-section"
              id="guide-questions"
            >
              <h2>Questions to ask at your visit</h2>
              <ul>
                {questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </section>
          )}
          {references.length > 0 && (
            <section
              id="guide-sources"
              className="reader-section reader-sources"
            >
              <h2>Sources</h2>
              <ul>
                {references.map((source) => {
                  const url =
                    source.publisher === "World Health Organization"
                      ? whoSources[source.label]
                      : null;
                  return (
                    <li key={source.label}>
                      {url ? (
                        <a href={url}>
                          {source.label}{" "}
                          <ArrowUpRight size={15} aria-hidden="true" />
                        </a>
                      ) : (
                        <span>{source.label}</span>
                      )}
                      <span className="small muted">{source.publisher}</span>
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </article>
        <aside className="reader-aside">
          {sections.length > 0 && (
            <nav className="resource-help" aria-label="In this guide">
              <h2>In this guide</h2>
              <ol>
                {sections.map((section, index) => (
                  <li key={section.heading}>
                    <Link to={`#guide-section-${index + 1}`}>
                      {section.heading}
                    </Link>
                  </li>
                ))}
                {questions.length > 0 && (
                  <li>
                    <Link to="#guide-questions">Questions to ask</Link>
                  </li>
                )}
                {references.length > 0 && (
                  <li>
                    <Link to="#guide-sources">Sources</Link>
                  </li>
                )}
              </ol>
            </nav>
          )}
          {serviceNames.length > 0 && (
            <section className="resource-help">
              <h2>Find this care</h2>
              <ul className="plain-links">
                {serviceNames.map((service) => (
                  <li key={service.slug}>
                    <Link to={`/find-care/facilities?service=${service.slug}`}>
                      <Search size={14} aria-hidden="true" /> {service.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {related.length > 0 && (
            <section className="resource-help">
              <h2>Related guides</h2>
              <ul className="plain-links">
                {related.map((guide) => (
                  <li key={guide.slug}>
                    <Link to={`/health-library/${guide.slug}`}>
                      {guide.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <Link to="/assistant" className="btn btn-secondary btn-sm">
            Ask the health assistant
          </Link>
        </aside>
      </div>
    </div>
  );
}
