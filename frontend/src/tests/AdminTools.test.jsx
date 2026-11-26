import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AdminMessages from "../pages/dashboard/AdminMessages";
import AdminUsers from "../pages/dashboard/AdminUsers";
import { ToastProvider } from "../components/Toast";
import { AuthProvider } from "../hooks/useAuth";
import { api, setToken } from "../services/api";

afterEach(() => {
  setToken(null);
  vi.restoreAllMocks();
});

const page = (items) => ({ items, total: items.length, page: 1, pages: 1, page_size: 20 });

function renderPage(element) {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <ToastProvider>{element}</ToastProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("admin contact messages", () => {
  it("filters by topic and searches sender, email, message and reference", async () => {
    const messages = vi.spyOn(api, "adminMessages").mockResolvedValue(
      page([
        {
          reference: "MSG-7", name: "Achieng Otieno", email: "achieng@example.com", topic: "privacy",
          message: "Please remove my phone number.", status: "new", created_at: "2026-11-20T08:00:00Z",
        },
      ]),
    );
    renderPage(<AdminMessages />);
    expect(await screen.findByText("Achieng Otieno")).toBeInTheDocument();
    expect(screen.getByText(/MSG-7 ·/)).toHaveTextContent("Privacy or data request");
    expect(messages).toHaveBeenLastCalledWith({ status: "new", topic: "", q: "", page: 1 });

    fireEvent.change(screen.getByLabelText("Topic"), { target: { value: "privacy" } });
    await waitFor(() => expect(messages).toHaveBeenLastCalledWith({ status: "new", topic: "privacy", q: "", page: 1 }));

    fireEvent.change(screen.getByLabelText("Search messages"), { target: { value: "  MSG-7 " } });
    await waitFor(() => expect(messages).toHaveBeenLastCalledWith({ status: "new", topic: "privacy", q: "MSG-7", page: 1 }));

    // the status tabs still work together with the new filters
    fireEvent.click(screen.getByRole("tab", { name: "All" }));
    await waitFor(() => expect(messages).toHaveBeenLastCalledWith({ status: "", topic: "privacy", q: "MSG-7", page: 1 }));
  });
});

describe("admin staff accounts", () => {
  const facilityResults = ({ q }) =>
    Promise.resolve(
      q === "kisumu"
        ? { items: [{ slug: "lake-clinic-kisumu", name: "Lake Clinic", town: "Kisumu" }], total: 1 }
        : q === "nowhere"
          ? { items: [], total: 0 }
          : { items: [{ slug: "aga-khan-nairobi", name: "Aga Khan Hospital", town: "Nairobi" }], total: 630 },
    );

  function signedInAdmin() {
    setToken("admin-session");
    vi.spyOn(api, "me").mockResolvedValue({ id: 1, role: "admin", full_name: "Admin", email: "admin@example.com" });
    vi.spyOn(api, "adminUsers").mockResolvedValue(page([]));
  }

  it("finds any facility by name or town when creating a staff account", async () => {
    signedInAdmin();
    const facilities = vi.spyOn(api, "facilities").mockImplementation(facilityResults);
    const create = vi.spyOn(api, "createStaffAccount").mockResolvedValue({ id: 9 });
    renderPage(<AdminUsers />);

    fireEvent.click(await screen.findByRole("button", { name: /New staff account/ }));
    expect(await screen.findByRole("option", { name: "Aga Khan Hospital (Nairobi)" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: "Grace Wambui" } });
    fireEvent.change(screen.getByLabelText(/^Email/), { target: { value: "grace@example.com" } });
    fireEvent.change(screen.getByLabelText(/Temporary password/), { target: { value: "Welcome2026" } });
    fireEvent.change(screen.getByLabelText(/Find facility/), { target: { value: "kisumu" } });
    expect(await screen.findByRole("option", { name: "Lake Clinic (Kisumu)" })).toBeInTheDocument();
    expect(facilities).toHaveBeenLastCalledWith({ q: "kisumu", page_size: 40, sort: "name", hide_demo: false });

    fireEvent.change(screen.getByLabelText(/^Facility/), { target: { value: "lake-clinic-kisumu" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({
        full_name: "Grace Wambui", email: "grace@example.com", password: "Welcome2026",
        role: "facility_staff", facility_slug: "lake-clinic-kisumu",
      }),
    );
  });

  it("says when no facility matches and clears an earlier choice", async () => {
    signedInAdmin();
    vi.spyOn(api, "facilities").mockImplementation(facilityResults);
    renderPage(<AdminUsers />);

    fireEvent.click(await screen.findByRole("button", { name: /New staff account/ }));
    await screen.findByRole("option", { name: "Aga Khan Hospital (Nairobi)" });
    fireEvent.change(screen.getByLabelText(/^Facility/), { target: { value: "aga-khan-nairobi" } });
    expect(screen.getByLabelText(/^Facility/)).toHaveValue("aga-khan-nairobi");

    fireEvent.change(screen.getByLabelText(/Find facility/), { target: { value: "nowhere" } });
    expect(await screen.findByText("No facility matches that search.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Facility/)).toHaveValue("");
  });

  it("shows the server's reason when the demonstration email domain is refused", async () => {
    signedInAdmin();
    vi.spyOn(api, "facilities").mockImplementation(facilityResults);
    const { ApiError } = await import("../services/api");
    vi.spyOn(api, "createStaffAccount").mockRejectedValue(
      new ApiError("This email domain is reserved for demonstration accounts.", 400),
    );
    renderPage(<AdminUsers />);

    fireEvent.click(await screen.findByRole("button", { name: /New staff account/ }));
    fireEvent.change(await screen.findByLabelText(/^Role/), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: "Demo Helper" } });
    fireEvent.change(screen.getByLabelText(/^Email/), { target: { value: "helper@reprocare.demo" } });
    fireEvent.change(screen.getByLabelText(/Temporary password/), { target: { value: "Welcome2026" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("This email domain is reserved for demonstration accounts.")).toBeInTheDocument();
  });
});
