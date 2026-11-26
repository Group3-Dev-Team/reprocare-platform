import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../hooks/useAuth";
import ForgotPasswordPage from "../pages/ForgotPasswordPage";
import ResetPasswordPage from "../pages/ResetPasswordPage";
import { request } from "../services/api";

// fake the API so no real requests are sent
vi.mock("../services/api", async (importOriginal) => ({
  ...(await importOriginal()),
  request: vi.fn(),
}));

afterEach(() => vi.resetAllMocks());

function show(Page, path) {
  render(
    <MemoryRouter
      initialEntries={[path]}
    >
      <AuthProvider>
        <Page />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("password recovery", () => {
  it("offers support and does not offer to send email when recovery is unavailable", async () => {
    request.mockResolvedValue({ available: false });
    show(ForgotPasswordPage, "/forgot-password");
    expect(
      await screen.findByText(/online password recovery is unavailable/i),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /contact reprocare support/i }),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: /send reset link/i }),
    ).not.toBeInTheDocument();
  });

  it("submits a recovery request and renders a neutral acceptance message", async () => {
    request
      .mockResolvedValueOnce({ available: true })
      .mockResolvedValueOnce({});
    show(ForgotPasswordPage, "/forgot-password");
    fireEvent.change(await screen.findByLabelText(/^Email address/), {
      target: { value: "test@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(
      await screen.findByText(/if your account can be recovered by email/i),
    ).toBeVisible();
    expect(request).toHaveBeenLastCalledWith("POST", "/auth/recovery/request", {
      body: { email: "test@example.com" },
      anonymous: true,
    });
  });

  it("rejects mismatched passwords and posts the link token and confirmed new password once", async () => {
    request
      .mockResolvedValueOnce({ available: true })
      .mockResolvedValueOnce(null);
    const token = "X".repeat(43);
    show(ResetPasswordPage, "/reset-password#token=" + token);
    const update = await screen.findByRole("button", {
      name: "Update password",
    });
    fireEvent.change(screen.getByLabelText(/^New password/), {
      target: { value: "OnePass99" },
    });
    fireEvent.change(screen.getByLabelText(/^Confirm new password/), {
      target: { value: "OtherPass99" },
    });
    fireEvent.click(update);
    expect(
      screen.getByText("Enter the same password in both fields."),
    ).toBeVisible();
    expect(request).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText(/^Confirm new password/), {
      target: { value: "OnePass99" },
    });
    fireEvent.click(update);
    await waitFor(() =>
      expect(screen.getByText(/your password has been updated/i)).toBeVisible(),
    );
    expect(request).toHaveBeenCalledTimes(2);
    expect(request).toHaveBeenLastCalledWith("POST", "/auth/recovery/reset", {
      body: { token, new_password: "OnePass99" },
      anonymous: true,
    });
  });
});
