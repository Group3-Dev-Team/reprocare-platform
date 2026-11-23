import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AuthProvider } from "../hooks/useAuth";
import { ApiError, api, getToken, setToken } from "../services/api";

afterEach(() => {
  setToken(null);
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderDashboard() {
  return render(
    <MemoryRouter
      initialEntries={["/dashboard"]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <AuthProvider>
        <Routes>
          <Route path="/sign-in" element={<h1>Sign in</h1>} />
          <Route element={<ProtectedRoute roles={["patient"]} />}>
            <Route path="/dashboard" element={<h1>Patient dashboard</h1>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("frontend account session", () => {
  it("offers a retry on connection failure without losing the stored session or opening protected content", async () => {
    setToken("test-session");
    // first call fails (server down), second works
    const me = vi
      .spyOn(api, "me")
      .mockRejectedValueOnce(new ApiError("Unavailable", 0))
      .mockResolvedValueOnce({ id: 17, role: "patient" });

    renderDashboard();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We could not verify your ReproCare session",
    );
    expect(
      screen.queryByRole("heading", { name: "Patient dashboard" }),
    ).not.toBeInTheDocument();
    expect(getToken()).toBe("test-session");

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("heading", { name: "Patient dashboard" }),
    ).toBeVisible();
    expect(me).toHaveBeenCalledTimes(2);
  });

  it("clears expired sessions and redirects when the backend returns 401", async () => {
    setToken("expired-test-session");
    vi.spyOn(api, "me").mockRejectedValueOnce(
      new ApiError("Please sign in to continue", 401),
    );
    renderDashboard();
    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeVisible();
    expect(getToken()).toBeNull();
  });

  it("sends sign-in and registration without a previously saved authorization token", async () => {
    setToken("stale-test-session");
    const fetchMock = vi
      .fn()
      .mockImplementation(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await api.login({});
    await api.register({});

    expect(
      fetchMock.mock.calls.map(
        ([path]) => new URL(path, window.location.origin).pathname,
      ),
    ).toEqual(["/api/auth/login", "/api/auth/register"]);
    for (const [, options] of fetchMock.mock.calls) {
      expect(options.method).toBe("POST");
      expect(options.headers).not.toHaveProperty("Authorization");
    }
  });
});
