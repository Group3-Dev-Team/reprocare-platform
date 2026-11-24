import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { CompareProvider } from "../hooks/useCompare";
import { api } from "../services/api";
import ComparePage from "../pages/ComparePage";
import VisitPreparationPage from "../pages/VisitPreparationPage";

afterEach(() => vi.restoreAllMocks());

function CurrentSearch() {
  return (
    <output aria-label="Current URL query">
      {useLocation().search || "No query"}
    </output>
  );
}

function renderCareGuide() {
  render(
    <MemoryRouter
      initialEntries={["/compare"]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <CompareProvider>
        <Routes>
          <Route path="/compare" element={<ComparePage />} />
          <Route
            path="/prepare-for-your-visit"
            element={<VisitPreparationPage />}
          />
        </Routes>
        <CurrentSearch />
      </CompareProvider>
    </MemoryRouter>,
  );
}

it("suggests only services in the catalogue and carries a matching checklist without adding a goal to that URL", async () => {
  vi.spyOn(api, "services").mockResolvedValue([
    { slug: "antenatal", name: "Antenatal care" },
  ]);
  renderCareGuide();

  const goal = await screen.findByRole("combobox", { name: "Care goal" });
  expect(
    screen.getByRole("option", { name: "Plan pregnancy check-ups" }),
  ).toBeVisible();
  expect(
    screen.queryByRole("option", { name: "Find cervical screening" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Search for this service" }),
  ).not.toBeInTheDocument();

  fireEvent.change(goal, { target: { value: "antenatal" } });
  expect(screen.getByRole("heading", { name: "Antenatal care" })).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Search for this service" }),
  ).toHaveAttribute("href", "/find-care/facilities?service=antenatal");

  fireEvent.click(
    screen.getByRole("link", { name: "Prepare questions for your visit" }),
  );
  expect(
    await screen.findByRole("combobox", { name: "Visit purpose" }),
  ).toHaveValue("pregnancy");
  expect(
    screen.getByRole("status", { name: "Current URL query" }),
  ).toHaveTextContent("No query");
});

it("lets visitors prepare for a general consultation when the catalogue fails and allows retry", async () => {
  vi.spyOn(api, "services")
    .mockRejectedValueOnce(new Error("Offline"))
    .mockResolvedValue([{ slug: "fertility", name: "Fertility consultation" }]);
  renderCareGuide();

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Care options could not be loaded.",
  );
  expect(
    screen.getByRole("link", { name: "Prepare for a general consultation" }),
  ).toHaveAttribute("href", "/prepare-for-your-visit");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(
    await screen.findByRole("option", { name: "Discuss trying to conceive" }),
  ).toBeVisible();
});

const fixtureFacility = (slug, extra = {}) => ({
  slug,
  name: `Fixture ${slug}`,
  type_label: "Clinic",
  town: "Nakuru",
  county: "Nakuru",
  services: [],
  insurers: [],
  payment_methods: [],
  accessibility: [],
  rating: { average: null, count: 0 },
  registration_status: "not_checked",
  ...extra,
});

function renderAssistant(url) {
  localStorage.setItem(
    "reprocare.compare",
    JSON.stringify([
      { slug: "one", name: "Fixture one" },
      { slug: "two", name: "Fixture two" },
    ]),
  );
  render(
    <MemoryRouter
      initialEntries={[url]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <CompareProvider>
        <Routes>
          <Route path="/compare" element={<ComparePage />} />
        </Routes>
      </CompareProvider>
    </MemoryRouter>,
  );
}

it("shows a per-facility error and retry when public reviews fail, instead of implying no rating", async () => {
  vi.spyOn(api, "services").mockResolvedValue([]);
  vi.spyOn(api, "facility").mockImplementation(async (slug) =>
    fixtureFacility(slug),
  );
  const summary = vi
    .spyOn(api, "facilityPublicFeedback")
    .mockImplementation(async (slug) => {
      if (slug === "two") throw new Error("Offline");
      return { total_comments: 3, google: null, platforms: [] };
    });
  renderAssistant("/compare?topic=reviews");

  expect(
    await screen.findByText(
      "3 written public comments from linked social accounts.",
    ),
  ).toBeVisible();
  expect(
    screen.getByText("No Google rating is recorded for this listing."),
  ).toBeVisible();
  expect(
    await screen.findByText("Public reviews could not be loaded."),
  ).toBeVisible();

  summary.mockResolvedValue({ total_comments: 0, google: null, platforms: [] });
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(
    await screen.findAllByText(
      "No written public comments are recorded for this listing.",
    ),
  ).toHaveLength(2);
  expect(
    screen.queryByText("Public reviews could not be loaded."),
  ).not.toBeInTheDocument();
  localStorage.removeItem("reprocare.compare");
});

it("lists phone, email and website contacts and no longer offers the legacy table", async () => {
  vi.spyOn(api, "services").mockResolvedValue([]);
  vi.spyOn(api, "facility").mockImplementation(async (slug) =>
    fixtureFacility(
      slug,
      slug === "one"
        ? {
            phone: "+254 700 000 001",
            email: "desk@example.org",
            website: "example.org",
          }
        : {},
    ),
  );
  renderAssistant("/compare?topic=access&view=details");

  expect(
    await screen.findByRole("link", { name: "Email desk@example.org" }),
  ).toHaveAttribute("href", "mailto:desk@example.org");
  expect(screen.getByRole("link", { name: /Visit website/ })).toHaveAttribute(
    "href",
    "https://example.org",
  );
  expect(screen.getByText("No contact details are recorded.")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "View detailed table" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  localStorage.removeItem("reprocare.compare");
});
