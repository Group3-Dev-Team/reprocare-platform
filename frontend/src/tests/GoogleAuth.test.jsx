import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import GoogleAuthButton, {
  GOOGLE_ATTEMPT_KEY,
} from "../components/GoogleAuthButton";
import { AuthProvider } from "../hooks/useAuth";
import { GoogleLinkPanel } from "../components/GoogleLinkPanel";
import GoogleCallbackPage from "../pages/GoogleCallbackPage";
import { api, getToken, setToken } from "../services/api";

afterEach(() => {
  sessionStorage.clear();
  setToken(null);
  vi.restoreAllMocks();
});

function callback(route) {
  return render(
    <MemoryRouter
      initialEntries={[route]}
    >
      <AuthProvider>
        <Routes>
          <Route
            path="/auth/google/callback"
            element={<GoogleCallbackPage />}
          />
          <Route path="/dashboard" element={<h1>Patient workspace</h1>} />
          <Route
            path="/dashboard/account"
            element={<h1>Account settings</h1>}
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Google sign-in", () => {
  it("only offers Google when the server enables the integration", async () => {
    const capabilities = vi
      .spyOn(api, "authCapabilities")
      .mockResolvedValue({ google: false });
    render(<GoogleAuthButton />);
    await waitFor(() => expect(capabilities).toHaveBeenCalled());
    expect(
      screen.queryByRole("button", { name: "Sign in with Google" }),
    ).toBeNull();
  });

  it("never exchanges an authorization code in a tab that did not start its flow", async () => {
    const exchange = vi.spyOn(api, "googleExchange");
    callback("/auth/google/callback?code=test-code&state=unexpected");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "different browser tab",
    );
    expect(exchange).not.toHaveBeenCalled();
  });

  it("exchanges a matching state and clears the one-use browser verifier", async () => {
    sessionStorage.setItem(
      GOOGLE_ATTEMPT_KEY,
      JSON.stringify({ state: "expected", verifier: "test-proof" }),
    );
    const exchange = vi
      .spyOn(api, "googleExchange")
      .mockResolvedValue({ token: "test-token", user: { role: "patient" } });
    callback("/auth/google/callback?code=test-code&state=expected");
    expect(
      await screen.findByRole("heading", { name: "Patient workspace" }),
    ).toBeInTheDocument();
    expect(exchange).toHaveBeenCalledTimes(1);
    expect(exchange).toHaveBeenCalledWith({
      code: "test-code",
      state: "expected",
      verifier: "test-proof",
    });
    expect(sessionStorage.getItem(GOOGLE_ATTEMPT_KEY)).toBeNull();
  });
});

describe("Connect Google from account settings", () => {
  it("shows the connection from server-confirmed status", async () => {
    vi.spyOn(api, "googleLinkStatus").mockResolvedValue({
      available: true,
      linked: true,
    });
    render(<GoogleLinkPanel />);
    expect(
      await screen.findByText("Your Google account is connected to ReproCare."),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "Connect Google account" }),
    ).toBeNull();
  });

  it("finishes linking through the authenticated route and preserves the current session", async () => {
    setToken("existing-test-token");
    vi.spyOn(api, "me").mockResolvedValue({ id: 9, role: "patient" });
    sessionStorage.setItem(
      GOOGLE_ATTEMPT_KEY,
      JSON.stringify({
        state: "link-state",
        verifier: "link-proof",
        intent: "link",
      }),
    );
    const link = vi.spyOn(api, "googleLinkExchange").mockResolvedValue(null);
    const signIn = vi.spyOn(api, "googleExchange");

    callback("/auth/google/callback?code=test-code&state=link-state");
    expect(
      await screen.findByRole("heading", { name: "Account settings" }),
    ).toBeInTheDocument();
    expect(link).toHaveBeenCalledWith({
      code: "test-code",
      state: "link-state",
      verifier: "link-proof",
    });
    expect(signIn).not.toHaveBeenCalled();
    expect(getToken()).toBe("existing-test-token");
    expect(sessionStorage.getItem(GOOGLE_ATTEMPT_KEY)).toBeNull();
  });
});
