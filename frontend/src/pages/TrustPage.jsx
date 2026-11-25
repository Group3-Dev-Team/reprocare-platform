import { Link } from "react-router-dom";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PageHeader } from "../components/PageHeader";
import { SourceLabel } from "../components/Badges";

const layers = [
  {
    layer: "registry",
    label: "Registry record matched",
    title: "Official registration",
    body: "We compare a listing with a public register, such as the Kenya Master Health Facility List or a professional council register. When the name, location and type match, we show the register, its reference and the date we checked.",
    means: "A record exists in that register on the date shown.",
    notMeans: "It is not an inspection, a quality rating or a recommendation.",
  },
  {
    layer: "provider",
    label: "Stated by the facility",
    title: "Provider-stated details",
    body: "Services, opening hours, contacts, payment methods and insurers come from the facility or practitioner. Facility staff update them from their ReproCare workspace.",
    means: "This is what the provider tells patients.",
    notMeans:
      "We have not visited to confirm it. Call ahead before travelling.",
  },
  {
    layer: "patient",
    label: "ReproCare review",
    title: "Patient experiences",
    body: "Reviews are written by people with a ReproCare account and checked by a moderator for personal information, abuse and relevance before publication.",
    means:
      "One person’s experience of waiting time, communication, privacy or cost.",
    notMeans:
      "Not a clinical outcome, and a few reviews cannot represent every patient.",
  },
  {
    layer: "unverified",
    label: "Not yet checked",
    title: "Unverified or unresolved",
    body: "Some listings have not been compared with a register yet, or the match was uncertain. We say so rather than leaving the label off.",
    means: "Treat the details with extra care and confirm them directly.",
    notMeans: "It does not mean the facility is unregistered.",
  },
];

export default function TrustPage() {
  useDocumentTitle(
    "Our approach to trust",
    "How ReproCare labels registration records, provider-stated details, patient experiences and unverified information.",
  );
  return (
    <div className="about-editorial trust-editorial">
      <PageHeader
        title="Know where your information comes from"
        intro="Healthcare decisions deserve reliable information. ReproCare keeps official records, provider statements and patient feedback apart, and labels each one, so you can judge them for what they are."
        crumbs={[
          { label: "About ReproCare", to: "/about" },
          { label: "Our approach to trust" },
        ]}
      />
      <section className="section">
        <div className="container">
          <div className="section-head">
            <h2>The labels you will see</h2>
          </div>
          <div className="layer-table">
            {layers.map((l) => (
              <article
                key={l.layer}
                className={`layer-row layer-row-${l.layer}`}
              >
                <div>
                  <SourceLabel layer={l.layer}>{l.label}</SourceLabel>
                  <h3>{l.title}</h3>
                  <p>{l.body}</p>
                </div>
                <dl>
                  <dt>What it tells you</dt>
                  <dd>{l.means}</dd>
                  <dt>What it does not</dt>
                  <dd>{l.notMeans}</dd>
                </dl>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-tinted">
        <div className="container prose-split">
          <div>
            <h2>External platforms</h2>
            <p>
              Public Reviews shows source-labelled activity from Facebook,
              Google and TikTok where available. When a Facebook page
              serves an organisation with multiple branches, its activity is
              labelled as organisation-wide. Google Maps ratings and any
              available written reviews retain their own attribution.
            </p>
            <p>
              Public platform activity is shown for context. It does not affect
              ReproCare ratings or ranking. Moderated ReproCare patient reviews
              appear separately. ReproCare shortens names and masks contact
              details in its collected social comments.
            </p>
            <p>
              When we cannot show a source because its terms or permissions do
              not allow it, we say so instead of filling the gap.
            </p>
          </div>
          <div>
            <h2>Rules that money cannot change</h2>
            <ul className="check-list">
              <li>
                No one can pay for a registry label, a better position in
                results or the removal of a review.
              </li>
              <li>
                Facilities can reply to reviews publicly, but cannot edit or
                delete them.
              </li>
              <li>
                We do not sell personal information or search histories to
                anyone.
              </li>
              <li>
                We never invent reviews, quotations or verification claims.
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container prose-split">
          <div>
            <h2>How moderation works</h2>
            <ol>
              <li>
                A signed-in patient writes about a visit and agrees to
                publication.
              </li>
              <li>
                A moderator checks for personal health details, names, abuse and
                relevance.
              </li>
              <li>
                The review is published or returned with a reason, and the
                author is notified.
              </li>
              <li>The facility may reply publicly.</li>
            </ol>
          </div>
          <div>
            <h2>Spotted something wrong?</h2>
            <p>
              Listings change. If a phone number, service or opening time is out
              of date, tell us and we will review it. Facilities can also
              correct their own details.
            </p>
            <Link
              className="btn btn-primary"
              to="/contact?topic=listing_correction"
            >
              Report a listing error
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
