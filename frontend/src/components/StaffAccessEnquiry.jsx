import { useEffect, useId, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useFetch } from "../hooks/useFetch";
import { facilityDisplayName } from "../data/facilityNames";
import { Field, Select, TextInput } from "./Forms";
import "../styles/discovery.css";

const ROLES = [
  "Doctor",
  "Nurse",
  "Clinical Officer",
  "Receptionist",
  "Facility Administrator",
  "Other",
];
const OPTIONS = ROLES.map((role) => ({ value: role, label: role }));

// staff can't make their own accounts, this sends a request to the admin through the contact form
export function StaffAccessEnquiry() {
  const navigate = useNavigate();
  const listId = useId();
  const [facility, setFacility] = useState("");
  const [chosen, setChosen] = useState(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [role, setRole] = useState("");
  const [otherRole, setOtherRole] = useState("");
  const [facilityError, setFacilityError] = useState("");
  const [roleError, setRoleError] = useState("");
  const text = facility.trim();
  const targetQuery = !chosen && text.length >= 2 ? text : "";

  // wait a moment after typing before searching
  useEffect(() => {
    const timer = window.setTimeout(
      () => setQuery(targetQuery),
      targetQuery ? 180 : 0,
    );
    return () => window.clearTimeout(timer);
  }, [targetQuery]);

  const results = useFetch(
    (signal) =>
      api.facilities(
        {
          ...(query ? { q: query } : {}),
          sort: query ? "relevance" : "name",
          hide_demo: true,
          page_size: 7,
        },
        { signal },
      ),
    [query],
  );
  const loading = results.loading || targetQuery !== query;
  const suggestions = loading ? [] : results.data?.items || [];
  const listOpen = open && suggestions.length > 0;

  useEffect(() => {
    if (listOpen && active >= 0) {
      document
        .getElementById(listId + "-" + active)
        ?.scrollIntoView?.({ block: "nearest" });
    }
  }, [active, listId, listOpen]);

  function selectFacility(item) {
    setFacility(facilityDisplayName(item));
    setChosen(item);
    setFacilityError("");
    setActive(-1);
    setOpen(false);
  }

  // arrow keys, enter and escape for the suggestion list
  function handleKeys(event) {
    if (event.key === "Escape" && open) {
      event.preventDefault();
      setOpen(false);
      setActive(-1);
    }
    if (
      (event.key === "ArrowDown" || event.key === "ArrowUp") &&
      suggestions.length
    ) {
      event.preventDefault();
      setOpen(true);
      const adjustment = event.key === "ArrowDown" ? 1 : -1;
      setActive((current) =>
        current < 0 && adjustment < 0
          ? suggestions.length - 1
          : (current + adjustment + suggestions.length) % suggestions.length,
      );
    }
    if (event.key === "Enter" && listOpen && suggestions[active]) {
      event.preventDefault();
      selectFacility(suggestions[active]);
    }
  }

  function submit(event) {
    event.preventDefault();
    if (!text) {
      setFacilityError("Enter the name of the facility.");
      return;
    }
    const facilityLabel = [text, chosen?.town].filter(Boolean).join(" · ");
    const roleLabel = role === "Other" ? otherRole.trim() : role;
    if (!roleLabel) {
      setRoleError("Enter your role at the facility.");
      return;
    }
    // open the contact page with the message already filled in
    navigate("/contact?topic=general", {
      state: {
        draft: `Staff access enquiry\nFacility: ${facilityLabel}\nRole: ${roleLabel}\n`,
      },
    });
  }

  return (
    <section className="auth-staff-help stack">
      <h2>Healthcare staff access</h2>
      <p className="muted">
        Staff accounts are not self-registered. Choose your facility and role,
        then add your contact details on the next page and send the enquiry.
        An administrator checks your affiliation with the facility before
        creating a staff account; until then you have no staff access.
      </p>
      <form className="stack" onSubmit={submit}>
        <div className="staff-facility-picker">
          <Field
            label="Facility or clinic"
            hint="Choose a directory match or enter the facility name."
            error={facilityError}
            required
          >
            {(field) => (
              <input
                className="input"
                {...field}
                role="combobox"
                autoComplete="off"
                aria-autocomplete="list"
                aria-expanded={listOpen}
                aria-controls={listOpen ? listId : undefined}
                aria-activedescendant={
                  listOpen && suggestions[active]
                    ? listId + "-" + active
                    : undefined
                }
                maxLength={160}
                value={facility}
                onFocus={() => setOpen(true)}
                onClick={() => setOpen(true)}
                onBlur={() => {
                  setOpen(false);
                  setActive(-1);
                }}
                onKeyDown={handleKeys}
                onChange={(event) => {
                  setFacility(event.target.value);
                  setChosen(null);
                  setFacilityError("");
                  setActive(-1);
                  setOpen(true);
                }}
              />
            )}
          </Field>
          {/* suggestions float over the form so the fields below don't jump */}
          {open && (
            <div className="staff-facility-popover">
              {open && loading && (
                <p className="small muted" role="status">
                  Searching facility listings…
                </p>
              )}
              {open && !loading && results.error && (
                <p className="small muted" role="status">
                  Directory suggestions are unavailable. You can enter a
                  facility name.
                </p>
              )}
              {open && !loading && !results.error && !suggestions.length && (
                <p className="small muted" role="status">
                  No directory match. You can enter a facility name.
                </p>
              )}
              {listOpen && (
                <ul
                  id={listId}
                  role="listbox"
                  aria-label="Facility suggestions"
                  className="staff-facility-options"
                >
                  {suggestions.map((item, index) => (
                    <li
                      role="option"
                      id={listId + "-" + index}
                      aria-selected={index === active}
                      key={item.slug}
                      onPointerDown={(event) => event.preventDefault()}
                      onClick={() => selectFacility(item)}
                    >
                      <strong>{facilityDisplayName(item)}</strong>
                      <span className="small muted">
                        {[item.town, item.type_label]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {chosen && (
            <p className="small muted" role="status">
              Selected listing{chosen.town ? " in " + chosen.town : ""}.
            </p>
          )}
        </div>
        <Select
          label="Role at the facility"
          value={role}
          placeholder="Choose a role"
          options={OPTIONS}
          onChange={(event) => {
            setRole(event.target.value);
            setRoleError("");
          }}
          required
        />
        {role === "Other" && (
          <TextInput
            label="Your role"
            value={otherRole}
            error={roleError}
            onChange={(event) => {
              setOtherRole(event.target.value);
              setRoleError("");
            }}
            maxLength={120}
            required
          />
        )}
        <button className="btn btn-primary" type="submit">
          Continue: add your contact details
        </button>
      </form>
      <Link to="/sign-in">Sign in with an existing staff account</Link>
    </section>
  );
}
