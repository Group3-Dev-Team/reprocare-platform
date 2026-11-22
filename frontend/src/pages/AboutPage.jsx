import { Link } from "react-router-dom";
import {
  BookOpen,
  Building2,
  HandHeart,
  HeartHandshake,
  Search,
  ShieldCheck,
  Target,
  Users,
} from "lucide-react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import careConversation from "../assets/about-care-conversation.webp";
import careConversationSmall from "../assets/about-care-conversation-small.webp";
import { PageHeader } from "../components/PageHeader";

export default function AboutPage() {
  useDocumentTitle(
    "About ReproCare",
    "ReproCare is an independent reproductive healthcare discovery platform for Kenya.",
  );
  return (
    <div className="about-editorial">
      <PageHeader
        title="Reproductive healthcare information people in Kenya can check"
        intro="ReproCare is an independent discovery service. We help people find suitable reproductive healthcare, understand what is known about each provider, and take a practical next step."
        crumbs={[{ label: "About ReproCare" }]}
        aside={
          <img
            className="header-photo"
            src={careConversation}
            srcSet={
              careConversationSmall + " 560w, " + careConversation + " 1000w"
            }
            sizes="(max-width: 800px) calc(100vw - 40px), (max-width: 1111px) 36vw, 400px"
            alt="A healthcare professional and a patient talking in a consultation room"
            width="1000"
            height="750"
            decoding="async"
          />
        }
      />
      <section className="section">
        <div className="container prose-split about-story">
          <div className="about-story-card">
            <span className="about-icon about-icon-violet">
              <Target size={22} aria-hidden="true" />
            </span>
            <h2>The problem we set out to solve</h2>
            <p>
              Someone looking for cervical screening, a first antenatal visit or
              a fertility assessment can usually find a facility on a map. What
              they often cannot find is whether that facility actually offers
              the service, whether it accepts their insurer, when it is open,
              and whether its phone line is answered.
            </p>
            <p>
              Online, registration records, a clinic’s own description and
              patient reviews are mixed together, even though each answers a
              different question. Free screening days and community programmes
              are announced on posters, radio and social media and are easy to
              miss.
            </p>
          </div>
          <div className="about-story-card about-story-card-accent">
            <span className="about-icon about-icon-blue">
              <ShieldCheck size={22} aria-hidden="true" />
            </span>
            <h2>What ReproCare does</h2>
            <p>
              We bring facility details, services, opening hours, reported
              insurers, community programmes and moderated patient experiences
              into one searchable directory. Every detail carries its source: an
              official register, the facility itself, or a patient.
            </p>
            <p>
              From a listing you can call, get directions, save the facility,
              compare it with others, or send an appointment request if the
              facility accepts requests through ReproCare.
            </p>
          </div>
        </div>
      </section>

      <section className="section section-tinted">
        <div className="container">
          <div className="section-head">
            <h2>Who ReproCare is for</h2>
          </div>
          <div className="grid-3">
            <div className="panel about-audience">
              <span className="about-icon about-icon-blue">
                <HeartHandshake size={22} aria-hidden="true" />
              </span>
              <h3>People seeking care</h3>
              <p className="muted">
                Women, men, couples and young people looking for pregnancy care,
                family planning, testing, screening or fertility advice, without
                needing an account to browse.
              </p>
            </div>
            <div className="panel about-audience">
              <span className="about-icon about-icon-mint">
                <Users size={22} aria-hidden="true" />
              </span>
              <h3>Families and supporters</h3>
              <p className="muted">
                Partners and relatives helping someone find a facility, prepare
                questions or register for a community programme.
              </p>
            </div>
            <div className="panel about-audience">
              <span className="about-icon about-icon-violet">
                <Building2 size={22} aria-hidden="true" />
              </span>
              <h3>Facilities and community health teams</h3>
              <p className="muted">
                Facility staff keep their listing accurate and respond to
                appointment requests; programme organisers reach the people
                their sessions are for.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <h2>How the parts work together</h2>
            <p className="lede">
              Discovery, education and community information each answer a
              different question on the way to care.
            </p>
          </div>
          <ul className="feature-grid">
            <li>
              <Search size={22} aria-hidden="true" />
              <h3>Find care</h3>
              <p>
                Search hospitals, clinics, laboratories and practitioners by
                service, town, hours and insurer.
              </p>
              <Link to="/find-care/facilities">Search facilities</Link>
            </li>
            <li>
              <ShieldCheck size={22} aria-hidden="true" />
              <h3>Check the source</h3>
              <p>
                See which details come from a register, which from the facility
                and which from patients.
              </p>
              <Link to="/trust">How we label sources</Link>
            </li>
            <li>
              <BookOpen size={22} aria-hidden="true" />
              <h3>Understand your options</h3>
              <p>
                Read plain-language guides and ask the assistant general
                questions in English or Kiswahili.
              </p>
              <Link to="/health-library">Health library</Link>
            </li>
            <li>
              <HandHeart size={22} aria-hidden="true" />
              <h3>Join community programmes</h3>
              <p>
                Look for listed screening days and education sessions, and
                register where the organiser offers it.
              </p>
              <Link to="/health-community/programmes">Programmes</Link>
            </li>
          </ul>
        </div>
      </section>

      <section className="section section-tinted">
        <div className="container prose-split">
          <div>
            <h2>What ReproCare is not</h2>
            <ul className="check-list">
              <li>
                Not a healthcare provider. We do not diagnose, prescribe or give
                treatment.
              </li>
              <li>
                Not a regulator. A registry match shows a record exists; it is
                not an inspection.
              </li>
              <li>Not an insurer. Your insurer decides what is covered.</li>
              <li>
                Not an emergency service. In an emergency call 999 or 112.
              </li>
            </ul>
          </div>
          <div>
            <h2>Our commitments</h2>
            <ul className="check-list">
              <li>
                Discovery is free, and nobody can pay for a higher place in
                search results.
              </li>
              <li>We never sell personal information or search histories.</li>
              <li>
                We say plainly when information is missing, old or unverified.
              </li>
              <li>
                A request is never shown as a confirmed appointment until the
                facility confirms it.
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container cta-band">
          <div>
            <h2>Start with the care you need</h2>
            <p>
              Search by service and town, then compare what each facility
              offers.
            </p>
          </div>
          <div className="row">
            <Link className="btn btn-primary btn-lg" to="/find-care/facilities">
              Find care
            </Link>
            <Link className="btn btn-secondary btn-lg" to="/contact">
              Contact us
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
