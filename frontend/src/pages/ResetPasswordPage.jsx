import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Alert } from "../components/Feedback";
import { PasswordInput } from "../components/Forms";
import { useAuth } from "../hooks/useAuth";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useFetch } from "../hooks/useFetch";
import { request } from "../services/api";
import { AuthAside } from "./RegisterPage";

export default function ResetPasswordPage() {
  useDocumentTitle(
    "Reset password",
    "Set a new password for your ReproCare account",
    { noIndex: true },
  );
  const { hash } = useLocation();
  const { verifySession } = useAuth();
  // the token comes after # in the email link
  const [token, setResetToken] = useState(
    () => new URLSearchParams(hash.slice(1)).get("token") || "",
  );
  const [error, setError] = useState(null);
  const [confirmError, setConfirmError] = useState("");
  const [busy, setBusy] = useState(false);
  const [updated, setUpdated] = useState(false);
  const validToken = /^[A-Za-z0-9_-]{43}$/.test(token);
  const {
    data,
    loading,
    error: availabilityError,
    reload,
  } = useFetch(
    (signal) =>
      validToken
        ? request("GET", "/auth/recovery/status", { signal, anonymous: true })
        : null,
    [validToken],
  );

  useEffect(() => {
    // remove the token from the address bar so it isn't saved in history or copied
    if (hash)
      window.history.replaceState(
        window.history.state,
        "",
        window.location.pathname,
      );
  }, [hash]);

  async function submit(event) {
    event.preventDefault();
    setConfirmError("");
    setError(null);
    const fields = new FormData(event.currentTarget);
    const password = String(fields.get("new_password") || "");
    if (!password) {
      setError({ fields: { new_password: "Enter a new password." } });
      return;
    }
    if (password !== fields.get("confirm_password")) {
      setConfirmError("Enter the same password in both fields.");
      return;
    }
    setBusy(true);
    try {
      await request("POST", "/auth/recovery/reset", {
        body: { token, new_password: password },
        anonymous: true,
      });
      setResetToken("");
      setUpdated(true);
      // the backend signed this account out everywhere, so refresh who is signed in
      verifySession();
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card stack">
        <h1>Reset password</h1>
        {updated ? (
          <>
            <p role="status">
              Your password has been updated. Sign in with your new password.
            </p>
            <Link className="btn btn-primary" to="/sign-in">
              Sign in
            </Link>
          </>
        ) : !validToken ? (
          <Alert tone="danger">
            This password reset link is missing or invalid.
          </Alert>
        ) : loading ? (
          <p role="status">Checking password recovery…</p>
        ) : availabilityError ? (
          <div className="stack">
            <Alert tone="danger">
              We could not check password recovery right now.
            </Alert>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={reload}
            >
              Try again
            </button>
          </div>
        ) : !data?.available ? (
          <p>
            Online password recovery is unavailable.{" "}
            <Link to="/contact?topic=technical">Contact ReproCare support</Link>{" "}
            for help.
          </p>
        ) : (
          <form className="stack" onSubmit={submit} noValidate>
            {error?.message && <Alert tone="danger">{error.message}</Alert>}
            <PasswordInput
              name="new_password"
              label="New password"
              autoComplete="new-password"
              required
              error={error?.fields?.new_password}
              hint="Use at least eight characters, including letters and a number."
            />
            <PasswordInput
              name="confirm_password"
              label="Confirm new password"
              autoComplete="new-password"
              required
              error={confirmError}
            />
            <button
              className="btn btn-primary"
              disabled={busy}
              aria-busy={busy}
            >
              {busy ? "Updating password…" : "Update password"}
            </button>
          </form>
        )}
        {!updated && (
          <Link to="/forgot-password">Request a new reset link</Link>
        )}
      </div>
      <AuthAside />
    </div>
  );
}
