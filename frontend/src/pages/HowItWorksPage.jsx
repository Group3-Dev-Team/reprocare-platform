import { Link } from "react-router-dom";
import {
  BadgeCheck,
  CalendarCheck,
  Columns3,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PageHeader } from "../components/PageHeader";
import { SourceLabel } from "../components/Badges";

const steps = [
  {
    icon: Search,
    title: "Search for the service first",
    body: "Choose the care you need, such as antenatal care, cervical screening or HIV testing, and a county. Service filters use the services recorded on each listing. If coverage is limited, browse nearby facilities and confirm services directly.",
    link: ["/find-care/facilities", "Start a search"],
  },
  {
    icon: SlidersHorizontal,
    title: "Narrow the results to what fits your life",
    body: "Filter by insurer, weekend or 24-hour opening, telehealth, and whether the facility takes appointment requests. Use the map, or your location, to see the nearest options first. You can also browse the directory without sharing your location.",
    link: ["/find-care/map", "Open the map"],
  },
  {
    icon: BadgeCheck,
    title: "Review the details and their sources",
    body: "A facility page shows services, hours, contacts, insurers, laboratory tests and practitioners. Each section is labelled with where the information comes from and when it was last checked.",
    link: ["/trust", "How sources are labelled"],
  },
  {
    icon: Columns3,
    title: "Compare up to three facilities",
    body: "Tick “Compare” on any result to see facilities side by side: services, opening hours, reported insurers, accessibility and moderated patient experiences.",
    link: ["/compare", "Open comparison"],
  },
  {
    icon: CalendarCheck,
    title: "Contact the facility or send a request",
    body: "Call or get directions straight from the listing. Where a facility takes requests through ReproCare, choose a preferred date and time. The facility confirms or declines, and you follow the status in your account.",
    link: ["/register", "Create a free account"],
  },
];

export default function HowItWorksPage() {
  useDocumentTitle(
    "How ReproCare works",
    "From searching for a service to requesting an appointment: how ReproCare helps you find reproductive healthcare in Kenya.",
  );
  return (
    <div className="about-editorial">
      <PageHeader
        title="How ReproCare works"
        intro="From a healthcare question to a practical next step, in five stages. You can browse everything without an account."
        crumbs={[
          { label: "About ReproCare", to: "/about" },
          { label: "How it works" },
        ]}
      />
      <section className="section">
        <div className="container">
          <ol className="timeline">
            {steps.map((s, i) => (
              <li key={s.title}>
                <span className="timeline-marker" aria-hidden="true">
                  {i + 1}
                </span>
                <div className="timeline-card">
                  <s.icon size={22} aria-hidden="true" />
                  <h2>{s.title}</h2>
                  <p>{s.body}</p>
                  <Link to={s.link[0]}>{s.link[1]}</Link>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section section-tinted">
        <div className="container">
          <div className="section-head">
            <h2>What each status means</h2>
            <p className="lede">
              Requests, confirmations and registrations are different events.
              ReproCare never treats one as another.
            </p>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>You will see</th>
                  <th>What it means</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <span className="badge badge-warning">
                      Awaiting facility
                    </span>
                  </td>
                  <td>
                    Your appointment request was delivered. The facility has not
                    answered yet, so the time is not booked.
                  </td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-success">
                      Confirmed by facility
                    </span>
                  </td>
                  <td>
                    Facility staff confirmed the request, often with a note
                    about the exact time or what to bring.
                  </td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-danger">Declined</span>
                  </td>
                  <td>
                    The facility could not take the request. Their note usually
                    explains why; you can contact them or choose another
                    facility.
                  </td>
                </tr>
                <tr>
                  <td>
                    <span className="badge badge-success">Registered</span>
                  </td>
                  <td>
                    You hold a place at a community programme. It is not a
                    record that any health service was given.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container prose-split">
          <div>
            <h2>What you do not need an account for</h2>
            <p>
              Searching, filtering, reading facility pages, comparing, using the
              map, reading the health library and asking the assistant are all
              open to everyone.
            </p>
          </div>
          <div>
            <h2>What an account adds</h2>
            <p>
              A free patient account lets you save facilities, send and track
              appointment requests, register for programmes and share your
              experience after a visit.
            </p>
            <div className="row">
              <SourceLabel layer="patient">Your data stays private</SourceLabel>
            </div>
          </div>
        </div>
        <div className="container cta-band" style={{ marginTop: 48 }}>
          <div>
            <h2>Ready to look?</h2>
            <p>Most searches take less than a minute.</p>
          </div>
          <Link className="btn btn-primary btn-lg" to="/find-care/facilities">
            Find care
          </Link>
        </div>
      </section>
    </div>
  );
}
