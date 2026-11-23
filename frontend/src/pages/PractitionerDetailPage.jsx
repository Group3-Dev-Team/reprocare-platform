import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CalendarDays,
  Clock,
  ClipboardList,
  MapPin,
  Users,
  Wallet,
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { useFetch } from "../hooks/useFetch";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { costTypes, formatDate, programTypes } from "../data/labels";
import { PageHeader } from "../components/PageHeader";
import { DemoLabel } from "../components/Badges";
import { MapView } from "../components/MapView";
import { RegistrationModal } from "../components/RegistrationModal";
import { Alert, ErrorState, LoadingState } from "../components/Feedback";
import NotFoundPage from "./NotFoundPage";

export default function ProgramDetailPage() {
  const { slug } = useParams();
  const { user } = useAuth();
  const result = useFetch(() => api.program(slug), [slug]);
  const [registering, setRegistering] = useState(false);
  const p = result.data;
  useDocumentTitle(p?.title, p?.summary);

  if (result.error?.status === 404) return <NotFoundPage what="programme" />;
  if (result.error)
    return (
      <div className="container section">
        <ErrorState error={result.error} onRetry={result.reload} />
      </div>
    );
  if (!p)
    return (
      <div className="container section">
        <LoadingState rows={2} />
      </div>
    );

  const full = p.spaces_left === 0;
  const pct = Math.min(100, Math.round((p.registered / p.capacity) * 100));

  return (
    <>
      <PageHeader
        title={p.title}
        intro={p.summary}
        tone="green"
        crumbs={[
          { label: "Health & community", to: "/health-community/programmes" },
          { label: "Programmes", to: "/health-community/programmes" },
          { label: p.title },
        ]}
      >
        <div className="row" style={{ gap: 6 }}>
          <span
            className={`badge ${p.cost_type === "free" ? "badge-success" : "badge-info"}`}
          >
            {costTypes[p.cost_type]}
          </span>
          <span className="badge">{programTypes[p.program_type]}</span>
          {p.service && (
            <span className="badge badge-rose">{p.service.name}</span>
          )}
          {p.is_demo && <DemoLabel />}
        </div>
      </PageHeader>
      <div className="container detail-layout section-sm">
        <div className="detail-main">
          <section className="panel">
            <h2>About this programme</h2>
            <p>{p.description}</p>
            <dl className="definition-list">
              <dt>Organised by</dt>
              <dd>{p.organizer_name}</dd>
              {p.host_facility && (
                <>
                  <dt>Hosted at</dt>
                  <dd>
                    <Link to={`/facilities/${p.host_facility.slug}`}>
                      {p.host_facility.name}
                    </Link>
                  </dd>
                </>
              )}
            </dl>
          </section>
          <section className="panel">
            <h2>Before you go</h2>
            <ul className="contact-list">
              <li>
                <Users size={16} aria-hidden="true" />
                <span>
                  <strong>Who can attend:</strong>{" "}
                  {p.eligibility || "Open to everyone"}
                </span>
              </li>
              <li>
                <ClipboardList size={16} aria-hidden="true" />
                <span>
                  <strong>What to bring:</strong>{" "}
                  {p.requirements || "Nothing specific"}
                </span>
              </li>
              <li>
                <Wallet size={16} aria-hidden="true" />
                <span>
                  <strong>Cost:</strong> {p.cost_note}
                </span>
              </li>
            </ul>
          </section>
          {p.latitude != null && (
            <section className="panel">
              <h2>Venue</h2>
              <p>{p.venue}</p>
              <MapView
                points={[
                  {
                    id: p.slug,
                    name: p.title,
                    latitude: p.latitude,
                    longitude: p.longitude,
                    subtitle: p.venue,
                    demo: p.is_demo,
                  },
                ]}
                selectedId={p.slug}
                zoom={14}
                height={260}
                label="Venue map"
              />
            </section>
          )}
        </div>
        <aside className="detail-side">
          <section className="panel register-panel">
            <ul className="contact-list">
              <li>
                <CalendarDays size={16} aria-hidden="true" />{" "}
                {formatDate(p.start_date, {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </li>
              <li>
                <Clock size={16} aria-hidden="true" /> {p.start_time} –{" "}
                {p.end_time}
              </li>
              <li>
                <MapPin size={16} aria-hidden="true" /> {p.venue}
              </li>
            </ul>
            <div className="capacity">
              <div className="spread small">
                <span>
                  {full ? "No places left" : `${p.spaces_left} places left`}
                </span>
                <span className="muted">{p.capacity} in total</span>
              </div>
              <div className="bar" aria-hidden="true">
                <span style={{ width: `${pct}%` }} />
              </div>
            </div>
            {p.is_past ? (
              <Alert tone="info">This programme has already taken place.</Alert>
            ) : full ? (
              <Alert tone="warning">
                This programme is full. Check other dates in the programme list.
              </Alert>
            ) : (
              (!user || user.role === "patient") && (
                <button
                  className="btn btn-success btn-block btn-lg"
                  onClick={() => setRegistering(true)}
                >
                  Register for this programme
                </button>
              )
            )}
            <p
              className="small muted"
              style={{ marginTop: 12, marginBottom: 0 }}
            >
              Registering holds a place. It does not record any health service,
              and your registration details are shared only with the organiser.
            </p>
          </section>
        </aside>
      </div>
      {registering && (
        <RegistrationModal
          program={p}
          onClose={() => setRegistering(false)}
          onDone={result.reload}
        />
      )}
    </>
  );
}
