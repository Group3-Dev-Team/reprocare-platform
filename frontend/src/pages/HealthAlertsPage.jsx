import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import {
  healthUpdatesForDate,
  kenyaWeeklyReports,
  preventionGuidance,
} from "../data/healthUpdates";
import { formatDate } from "../data/labels";
import "../styles/resource-pages.css";

const kenyaDate = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Africa/Nairobi",
});

function UpdateCard({ item }) {
  return (
    <article className="panel stack">
      <p className="small muted">
        {item.type} · {item.location}
      </p>
      <h3>{item.title}</h3>
      {item.status && (
        <p className="health-update-status">
          <strong>Status:</strong>{" "}
          {item.archived
            ? "Archived: check the official source for the current status"
            : item.status}
        </p>
      )}
      <p>{item.summary}</p>
      <p className="small muted">
        {item.publishedOn ? (
          <>
            Published{" "}
            <time dateTime={item.publishedOn}>
              {formatDate(item.publishedOn)}
            </time>
          </>
        ) : (
          <>
            Report data through{" "}
            <time dateTime={item.dataThrough}>
              {formatDate(item.dataThrough)}
            </time>
          </>
        )}
        {" · Source checked "}
        <time dateTime={item.checkedOn}>{formatDate(item.checkedOn)}</time>
      </p>
      <a href={item.url} rel="noopener noreferrer" target="_blank">
        Read the original update from {item.source}{" "}
        <ArrowUpRight size={15} aria-hidden="true" />
      </a>
    </article>
  );
}

export default function HealthAlertsPage() {
  useDocumentTitle(
    "Public health alerts",
    "Read dated public health updates from official sources in Kenya.",
  );
  const [params, setParams] = useSearchParams();
  const showArchive = params.get("archive") === "1";
  const updates = healthUpdatesForDate(kenyaDate.format(new Date()));
  const recent = updates.filter((item) => !item.archived);
  const archive = updates.filter((item) => item.archived);
  const show = (archived) => setParams(archived ? { archive: "1" } : {});
  const shown = showArchive ? archive : recent;

  return (
    <div className="resource-page">
      <PageHeader
        title="Public health alerts"
        intro="Dated updates from official sources for people in Kenya."
        crumbs={[
          { label: "Health & community", to: "/health-community/programmes" },
          { label: "Public health alerts" },
        ]}
      />
      <div className="container resource-main stack">
        <p>
          ReproCare checks these sources during editorial updates. For the
          latest situation, use the{" "}
          <a href={kenyaWeeklyReports}>WHO Kenya weekly reports</a> or the{" "}
          <a href="https://health.go.ke/">Kenya Ministry of Health</a>.
        </p>
        <div className="segmented" role="group" aria-label="Update period">
          <button
            type="button"
            aria-pressed={!showArchive}
            onClick={() => show(false)}
          >
            Recent updates
          </button>
          <button
            type="button"
            aria-pressed={showArchive}
            onClick={() => show(true)}
          >
            Archive
          </button>
        </div>
        <section className="stack" aria-labelledby="advisory-list-title">
          <h2 id="advisory-list-title">
            {showArchive ? "Archived updates" : "Recent updates"}
          </h2>
          {shown.length ? (
            shown.map((item) => <UpdateCard item={item} key={item.id} />)
          ) : (
            <p className="muted">
              {showArchive
                ? "No archived updates are listed."
                : "No recently checked reports are listed. Check the official sources for new updates."}
            </p>
          )}
        </section>
        <section className="stack" aria-labelledby="prevention-guidance-title">
          <h2 id="prevention-guidance-title">Prevention guidance</h2>
          <p className="small muted">
            General guidance from WHO. These fact sheets are not reports of a
            current outbreak in Kenya.
          </p>
          <ul className="health-guidance-list">
            {preventionGuidance.map((item) => (
              <li key={item.id}>
                <a href={item.url} rel="noopener noreferrer" target="_blank">
                  {item.topic}: {item.source} fact sheet{" "}
                  <ArrowUpRight size={14} aria-hidden="true" />
                  <span className="sr-only"> (opens in a new tab)</span>
                </a>
                <p className="small muted">{item.summary}</p>
              </li>
            ))}
          </ul>
        </section>
        <Link to="/health-library">Explore the Health Library</Link>
      </div>
    </div>
  );
}
