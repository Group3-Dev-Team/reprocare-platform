export const carePlanKey = "reprocare.tab-care-plan";
export const MAX_PLAN_FACILITIES = 6;

export const careSteps = [
  {
    id: "shortlist",
    label: "Shortlist a facility and check the location",
    to: "/find-care/facilities",
    link: "Find care",
  },
  {
    id: "contact",
    label: "Confirm services, hours and costs with the facility",
    to: "/compare",
    link: "Review care options",
  },
  {
    id: "prepare",
    label: "Prepare questions for the visit",
    to: "/prepare-for-your-visit",
    link: "Open the visit checklist",
  },
];

export function readCarePlan() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(carePlanKey));
    return {
      guides: Array.isArray(saved?.guides)
        ? saved.guides.filter((slug) => typeof slug === "string")
        : [],
      done: Array.isArray(saved?.done)
        ? saved.done.filter((id) => careSteps.some((step) => step.id === id))
        : [],
      facilities: Array.isArray(saved?.facilities)
        ? [
            ...new Set(
              saved.facilities.filter(
                (slug) =>
                  typeof slug === "string" && /^[a-z0-9-]{1,160}$/.test(slug),
              ),
            ),
          ].slice(0, MAX_PLAN_FACILITIES)
        : [],
    };
  } catch {
    return { guides: [], done: [], facilities: [] };
  }
}

export function writeCarePlan(next) {
  try {
    if (next.guides.length || next.done.length || next.facilities?.length)
      sessionStorage.setItem(carePlanKey, JSON.stringify(next));
    else sessionStorage.removeItem(carePlanKey);
    return true;
  } catch {
    return false;
  }
}
