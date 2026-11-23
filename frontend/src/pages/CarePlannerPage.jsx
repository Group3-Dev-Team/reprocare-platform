import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { ErrorState, LoadingState } from "../components/Feedback";
import { facilityDisplayName } from "../data/facilityNames";
import { careSteps, readCarePlan, writeCarePlan } from "../data/careplan";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useFetch } from "../hooks/useFetch";
import { api } from "../services/api";
import "../styles/resource-pages.css";

export default function CarePlannerPage() {
  useDocumentTitle(
    "Care planner",
    "Keep a guide reading list and track your next steps for this browser tab.",
  );
  const [plan, setPlan] = useState(readCarePlan);
  const [storageError, setStorageError] = useState(false);
  const listing = useFetch(
    (signal) =>
      plan.guides.length ? api.articles(undefined, { signal }) : null,
    [Boolean(plan.guides.length)],
  );
  const guides = (listing.data || []).filter((guide) =>
    plan.guides.includes(guide.slug),
  );
  const facilityKey = plan.facilities.join(",");
  const shortlist = useFetch(
    async (signal) => {
      const entries = await Promise.allSettled(
        plan.facilities.map((slug) => api.facility(slug, { signal })),
      );
      return entries.map((entry, index) => ({
        slug: plan.facilities[index],
        facility: entry.status === "fulfilled" ? entry.value : null,
      }));
    },
    [facilityKey],
  );
  const removeFacility = (slug) =>
    update({
      ...plan,
      facilities: plan.facilities.filter((item) => item !== slug),
    });

  const update = (next) => {
    setPlan(next);
    setStorageError(!writeCarePlan(next));
  };

  return (
    <div className="resource-page">
      <PageHeader
        title="Care planner"
        intro="Keep facilities, guides and visit preparations together in this tab."
      />
      <div className="container resource-main stack">
        <p>
          Your selections stay in this browser tab. Clear your plan before using
          a shared device, or close the tab when you finish.
        </p>
        {storageError && (
          <p role="status">
            Browser storage is unavailable. These changes last until you leave
            this page.
          </p>
        )}
        <section className="panel stack" aria-labelledby="care-facilities">
          <h2 id="care-facilities">Facilities in this plan</h2>
          {!plan.facilities.length && (
            <p>
              Open a facility listing and choose “Add to care plan” to shortlist
              it here.
            </p>
          )}
          {plan.facilities.length > 0 && shortlist.loading && (
            <LoadingState rows={2} height={35} label="Loading facilities" />
          )}
          {shortlist.data?.length > 0 && (
            <ul className="stack">
              {shortlist.data.map(({ slug, facility }) => (
                <li className="spread" key={slug}>
                  <div className="stack">
                    {facility ? (
                      <>
                        <Link to={`/facilities/${slug}`}>
                          {facilityDisplayName(facility)}
                        </Link>
                        <Link
                          className="small"
                          to={`/prepare-for-your-visit?facility=${slug}`}
                        >
                          Prepare for this visit
                        </Link>
                      </>
                    ) : (
                      <span className="small muted">
                        Facility listing unavailable
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    aria-label={
                      facility
                        ? `Remove ${facilityDisplayName(facility)} from care plan`
                        : "Remove unavailable facility"
                    }
                    onClick={() => removeFacility(slug)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
          {shortlist.data?.some(({ facility }) => !facility) && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={shortlist.reload}
            >
              Retry unavailable listings
            </button>
          )}
          <Link to="/find-care/facilities">Find facilities</Link>
        </section>
        <section className="panel stack" aria-labelledby="care-steps">
          <h2 id="care-steps">Next steps</h2>
          <ul className="stack">
            {careSteps.map((step) => {
              const checked = plan.done.includes(step.id);
              return (
                <li key={step.id}>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        update({
                          ...plan,
                          done: checked
                            ? plan.done.filter((item) => item !== step.id)
                            : [...plan.done, step.id],
                        })
                      }
                    />
                    {step.label}
                  </label>
                  <Link className="small" to={step.to}>
                    {step.link}
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
        <section className="panel stack" aria-labelledby="care-reading">
          <h2 id="care-reading">Reading list</h2>
          {plan.guides.length > 0 && listing.loading && (
            <LoadingState rows={2} height={35} label="Loading saved guides" />
          )}
          {listing.error && (
            <ErrorState error={listing.error} onRetry={listing.reload} />
          )}
          {guides.length > 0 ? (
            <ul className="stack">
              {guides.map((guide) => (
                <li className="spread" key={guide.slug}>
                  <Link to={`/health-library/${guide.slug}`}>
                    {guide.title}
                  </Link>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    aria-label={`Remove ${guide.title}`}
                    onClick={() =>
                      update({
                        ...plan,
                        guides: plan.guides.filter(
                          (slug) => slug !== guide.slug,
                        ),
                      })
                    }
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            (!plan.guides.length || (!listing.loading && !listing.error)) && (
              <p>
                Save a guide in the Health Library to read it later in this tab.
              </p>
            )
          )}
          <Link to="/health-library">Browse the Health Library</Link>
        </section>
        <div className="row">
          <Link className="btn btn-secondary" to="/dashboard/saved">
            My saved facilities
          </Link>
          <Link
            className="btn btn-secondary"
            to="/dashboard/appointments?view=agenda"
          >
            My appointment agenda
          </Link>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={
              !plan.guides.length &&
              !plan.done.length &&
              !plan.facilities.length
            }
            onClick={() => update({ guides: [], done: [], facilities: [] })}
          >
            Clear plan
          </button>
        </div>
      </div>
    </div>
  );
}
