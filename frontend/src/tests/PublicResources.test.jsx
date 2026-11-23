import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { townNames } from "../data/townNames";
import { healthUpdatesForDate } from "../data/healthUpdates";
import { carePlanKey, writeCarePlan } from "../data/carePlan";
import CarePlannerPage from "../pages/CarePlannerPage";
import LibraryPage from "../pages/LibraryPage";
import { PlanFacilityButton } from "../components/PlanFacilityButton";
import { api } from "../services/api";

afterEach(() => {
  sessionStorage.removeItem(carePlanKey);
  vi.restoreAllMocks();
});

describe("public health updates", () => {
  it("excludes future reports and archives an update at its review deadline", () => {
    expect(healthUpdatesForDate("2026-11-10")).toEqual([]);
    const updates = healthUpdatesForDate("2026-11-21");
    expect(updates).toHaveLength(2);
    expect(updates.map(({ archived }) => archived)).toEqual([false, false]);
    expect(
      healthUpdatesForDate("2026-11-28").map(({ archived }) => archived),
    ).toEqual([true, false]);
    expect(
      healthUpdatesForDate("2026-12-23").every(({ archived }) => archived),
    ).toBe(true);
  });
});

describe("care planner", () => {
  it("renders a saved guide and clears checked steps and saved topics from the tab", async () => {
    writeCarePlan({ guides: ["test-guide"], done: ["prepare"] });
    vi.spyOn(api, "articles").mockResolvedValue([
      { slug: "test-guide", title: "Test guide" },
    ]);
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <CarePlannerPage />
      </MemoryRouter>,
    );

    expect(
      await screen.findByRole("link", { name: "Test guide" }),
    ).toHaveAttribute("href", "/health-library/test-guide");
    expect(
      screen.getByRole("checkbox", { name: "Prepare questions for the visit" }),
    ).toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Clear plan" }));
    expect(
      screen.queryByRole("link", { name: "Test guide" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: "Prepare questions for the visit" }),
    ).not.toBeChecked();
    expect(sessionStorage.getItem(carePlanKey)).toBeNull();
  });
});

it("adds a facility to the tab plan and removes it without touching account saves", async () => {
  vi.spyOn(api, "facility").mockResolvedValue({
    slug: "fixture-clinic",
    name: "Fixture Clinic",
  });
  const accountSave = vi.spyOn(api, "save");
  render(
    <MemoryRouter
      initialEntries={["/fixtures"]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route
          path="/fixtures"
          element={<PlanFacilityButton slug="fixture-clinic" />}
        />
        <Route path="/care-planner" element={<CarePlannerPage />} />
      </Routes>
    </MemoryRouter>,
  );
  const add = screen.getByRole("button", { name: /add facility/i });
  fireEvent.click(add);
  expect(add).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("link", { name: "Open care planner" }));
  expect(
    await screen.findByRole("link", { name: "Fixture Clinic" }),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "Prepare for this visit" }),
  ).toHaveAttribute("href", "/prepare-for-your-visit?facility=fixture-clinic");
  fireEvent.click(
    screen.getByRole("button", {
      name: "Remove Fixture Clinic from care plan",
    }),
  );
  expect(
    screen.queryByRole("link", { name: "Fixture Clinic" }),
  ).not.toBeInTheDocument();
  expect(sessionStorage.getItem(carePlanKey)).toBeNull();
  expect(accountSave).not.toHaveBeenCalled();
});

it("shows reviewed questions in Kiswahili from the library", async () => {
  vi.spyOn(api, "articles").mockResolvedValue([]);
  render(
    <MemoryRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <LibraryPage />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Kiswahili" }));
  expect(
    screen.getByRole("heading", { name: "Maswali yanayoulizwa mara kwa mara" }),
  ).toBeVisible();
  const question = screen.getByText(
    "Nini hufanyika katika ziara ya kwanza ya kliniki ya wajawazito?",
  );
  expect(question.closest("details")).toBeInTheDocument();
  fireEvent.click(question);
  expect(
    screen.getByRole("link", {
      name: "Your first antenatal visit: what to expect",
    }),
  ).toHaveAttribute("href", "/health-library/first-antenatal-visit");
});

it("lists each town once when a town-only filter receives rows across counties", () => {
  expect(
    townNames([
      { town: "Shared Town", county: "County 1" },
      { town: "Another Town", county: "County 3" },
      { town: "SHARED TOWN", county: "County 2" },
      { town: null },
    ]),
  ).toEqual(["Another Town", "SHARED TOWN"]);
});
