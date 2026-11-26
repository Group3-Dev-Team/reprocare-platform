import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AdminArticles, { sectionsToText, textToSections } from "../pages/dashboard/AdminArticles";
import AdminPrograms from "../pages/dashboard/AdminPrograms";
import { ToastProvider } from "../components/Toast";
import { api } from "../services/api";
import reference from "../../../backend/app/database/reference_data.json";

afterEach(() => vi.restoreAllMocks());

function renderPage(element) {
  return render(
    <MemoryRouter>
      <ToastProvider>{element}</ToastProvider>
    </MemoryRouter>,
  );
}

const day = (offset) => new Date(Date.now() + offset * 864e5).toLocaleDateString("en-CA");

describe("article text format", () => {
  it("round-trips every seeded article body exactly", () => {
    expect(reference.articles.length).toBeGreaterThan(0);
    for (const article of reference.articles) {
      expect(textToSections(sectionsToText(article.sections))).toEqual({ sections: article.sections });
    }
  });

  it("explains what is wrong with a body it cannot save", () => {
    expect(textToSections("Text before any heading").error).toMatch(/Start the body with a section heading/);
    expect(textToSections("").error).toMatch(/at least one section/);
    expect(textToSections("## Empty\n\n## Full\nSome text").error).toMatch(/"Empty" needs at least one paragraph/);
    expect(textToSections("## Options\nFirst line\ncontinues here\n\n- Pills\n- Implants\n\nSecond paragraph")).toEqual({
      sections: [{ heading: "Options", paragraphs: ["First line continues here", "Second paragraph"], list: ["Pills", "Implants"] }],
    });
  });
});

const published = { slug: "contraception-options", title: "Comparing contraception options", category: "Family planning",
  summary: "How methods compare.", read_minutes: 6, related_services: ["contraception"], review_status: "Reviewed", updated_on: "2026-11-01", is_published: true };
const draft = { ...published, slug: "new-draft", title: "Preparing for a smear test", is_published: false };

describe("health library administration", () => {
  it("lists drafts and published articles and publishes a draft", async () => {
    vi.spyOn(api, "adminArticles").mockResolvedValue([published, draft]);
    vi.spyOn(api, "services").mockResolvedValue([]);
    const publish = vi.spyOn(api, "publishArticle").mockResolvedValue({ ...draft, is_published: true });
    renderPage(<AdminArticles />);

    const draftRow = (await screen.findByText("Preparing for a smear test")).closest("tr");
    expect(within(draftRow).getByText("Draft")).toBeInTheDocument();
    expect(within(draftRow).queryByRole("link")).toBeNull(); // drafts are not linked to the public page
    const publishedRow = screen.getByText("Comparing contraception options").closest("tr");
    expect(within(publishedRow).getByRole("link")).toHaveAttribute("href", "/health-library/contraception-options");

    fireEvent.click(within(draftRow).getByRole("button", { name: "Publish Preparing for a smear test" }));
    await waitFor(() => expect(publish).toHaveBeenCalledWith("new-draft"));
  });

  it("creates a draft in the stored article shape", async () => {
    vi.spyOn(api, "adminArticles").mockResolvedValue([]);
    vi.spyOn(api, "services").mockResolvedValue([{ slug: "cervical", name: "Cervical screening" }]);
    const create = vi.spyOn(api, "createArticle").mockResolvedValue({ slug: "x", is_published: false });
    renderPage(<AdminArticles />);

    fireEvent.click(await screen.findByRole("button", { name: /New article/ }));
    fireEvent.change(screen.getByLabelText(/^Title/), { target: { value: "Preparing for a smear test" } });
    fireEvent.change(screen.getByLabelText(/^Category/), { target: { value: "Screening" } });
    fireEvent.change(screen.getByLabelText(/^Summary/), { target: { value: "What happens during a smear test and how to prepare." } });
    fireEvent.change(screen.getByLabelText(/^Article text/), { target: { value: "## Before\nAvoid sex for two days.\n\n- Bring your ID\n\n## During\nIt takes five minutes." } });
    fireEvent.change(screen.getByLabelText(/^Questions/), { target: { value: "Does it hurt?\n\nWhen will I get results?" } });
    fireEvent.change(screen.getByLabelText(/^Sources/), { target: { value: "Cervical screening guide | Ministry of Health\nLocal clinic leaflet" } });
    fireEvent.click(await screen.findByLabelText("Cervical screening"));
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({
        title: "Preparing for a smear test", category: "Screening",
        summary: "What happens during a smear test and how to prepare.", read_minutes: 4,
        review_status: "Awaiting clinical review", related_services: ["cervical"],
        sections: [
          { heading: "Before", paragraphs: ["Avoid sex for two days."], list: ["Bring your ID"] },
          { heading: "During", paragraphs: ["It takes five minutes."] },
        ],
        questions_to_ask: ["Does it hurt?", "When will I get results?"],
        references: [{ label: "Cervical screening guide", publisher: "Ministry of Health" }, { label: "Local clinic leaflet", publisher: "" }],
      }),
    );
  });

  it("does not send a body it cannot save, and edits only what changed", async () => {
    const full = { ...reference.articles[0], related_services: ["contraception"], is_published: true };
    vi.spyOn(api, "adminArticles").mockResolvedValue([{ ...published, slug: full.slug, title: full.title }]);
    vi.spyOn(api, "services").mockResolvedValue([]);
    vi.spyOn(api, "adminArticle").mockResolvedValue(full);
    const update = vi.spyOn(api, "updateArticle").mockResolvedValue(full);
    renderPage(<AdminArticles />);

    fireEvent.click(await screen.findByRole("button", { name: `Edit ${full.title}` }));
    const body = await screen.findByLabelText(/^Article text/);
    expect(body.value).toBe(sectionsToText(full.sections));

    fireEvent.change(body, { target: { value: "No heading here" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(/Start the body with a section heading/)).toBeInTheDocument();
    expect(update).not.toHaveBeenCalled();

    fireEvent.change(body, { target: { value: sectionsToText(full.sections) } });
    fireEvent.change(screen.getByLabelText(/^Summary/), { target: { value: "A shorter, updated summary of the options." } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith(full.slug, { summary: "A shorter, updated summary of the options." }));
  });

  it("shows the server's explanation when saving fails", async () => {
    vi.spyOn(api, "adminArticles").mockResolvedValue([]);
    vi.spyOn(api, "services").mockResolvedValue([]);
    const { ApiError } = await import("../services/api");
    vi.spyOn(api, "createArticle").mockRejectedValue(new ApiError("Unknown related services: astrology.", 400));
    renderPage(<AdminArticles />);
    fireEvent.click(await screen.findByRole("button", { name: /New article/ }));
    fireEvent.change(screen.getByLabelText(/^Article text/), { target: { value: "## One\nText" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("Unknown related services: astrology.")).toBeInTheDocument();
  });
});

describe("programme attendance", () => {
  const program = (offset) => ({ slug: "screening-day", title: "Screening day", town: "Kisumu", cost_type: "free",
    start_date: day(offset), is_past: offset < 0, registered: 3, capacity: 10, status: "published" });
  const rows = [
    { reference: "REG-1", full_name: "Akinyi Odhiambo", phone: "0700000001", status: "registered" },
    { reference: "REG-2", full_name: "Wanjiru Kamau", phone: "0700000002", status: "attended" },
    { reference: "REG-3", full_name: "Halima Noor", phone: "0700000003", status: "cancelled" },
  ];

  it("records and undoes attendance on or after the programme date", async () => {
    vi.spyOn(api, "adminPrograms").mockResolvedValue([program(0)]);
    vi.spyOn(api, "services").mockResolvedValue([]);
    vi.spyOn(api, "programRegistrations").mockResolvedValue(rows);
    const mark = vi.spyOn(api, "setRegistrationStatus").mockImplementation((slug, ref, status) => Promise.resolve({ reference: ref, status }));
    renderPage(<AdminPrograms />);

    fireEvent.click(await screen.findByRole("button", { name: "Registrations" }));
    expect(await screen.findByText(/1 of 2 registered people attended/)).toBeInTheDocument();
    const cancelled = screen.getByText("Halima Noor").closest("tr");
    expect(within(cancelled).queryByRole("button")).toBeNull();

    fireEvent.click(within(screen.getByText("Akinyi Odhiambo").closest("tr")).getByRole("button", { name: "Mark attended" }));
    await waitFor(() => expect(mark).toHaveBeenCalledWith("screening-day", "REG-1", "attended"));
    expect(await screen.findByText(/2 of 2 registered people attended/)).toBeInTheDocument();

    fireEvent.click(within(screen.getByText("Wanjiru Kamau").closest("tr")).getByRole("button", { name: "Undo attended" }));
    await waitFor(() => expect(mark).toHaveBeenCalledWith("screening-day", "REG-2", "registered"));
  });

  it("explains that attendance opens on the programme date", async () => {
    vi.spyOn(api, "adminPrograms").mockResolvedValue([program(5)]);
    vi.spyOn(api, "services").mockResolvedValue([]);
    vi.spyOn(api, "programRegistrations").mockResolvedValue(rows.slice(0, 1));
    renderPage(<AdminPrograms />);

    fireEvent.click(await screen.findByRole("button", { name: "Registrations" }));
    expect(await screen.findByText(/Attendance can be recorded from/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark attended" })).toBeNull();
  });
});
