import { useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../components/Feedback";
import { TextInput } from "../components/Forms";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { useFetch } from "../hooks/useFetch";
import { request } from "../services/api";
import { AuthAside } from "./RegisterPage";

export default function ForgotPasswordPage() {
  useDocumentTitle("Forgot password", "Get help with your ReproCare account", {
    noIndex: true,
  });
  // first check if reset by email is turned on
  const {
    data,
    loading,
    error: availabilityError,
    reload,
  } = useFetch((signal) =>
    request("GET", "/auth/recovery/status", { signal, anonymous: true }),
  );
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(event) {
    event.preventDefault();
    const email = String(
      new FormData(event.currentTarget).get("email") || "",
    ).trim();
    if (!email) {
      setError({ fields: { email: "Enter your email address." } });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await request("POST", "/auth/recovery/request", {
        body: { email },
        anonymous: true,
      });
      setSent(true);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card stack">
        <h1>Forgot password?</h1>
        {loading && <p role="status">Checking password recovery…</p>}
        {availabilityError && (
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
        )}
        {!loading && !availabilityError && !data?.available && (
          <p>
            Online password recovery is unavailable. Contact ReproCare support
            for help with your account.
          </p>
        )}
        {/* same message after sending, so nobody can tell if an email has an account */}
        {data?.available &&
          (sent ? (
            <p role="status">
              If your account can be recovered by email, we’ll send a password
              reset link.
            </p>
          ) : (
            <form className="stack" onSubmit={submit} noValidate>
              <p>Enter the email address you use for ReproCare.</p>
              {error?.message && <Alert tone="danger">{error.message}</Alert>}
              <TextInput
                name="email"
                label="Email address"
                type="email"
                inputMode="email"
                autoComplete="email"
                required
                error={error?.fields?.email}
              />
              <button
                className="btn btn-primary"
                disabled={busy}
                aria-busy={busy}
              >
                {busy ? "Sending request…" : "Send reset link"}
              </button>
            </form>
          ))}
        <div className="row">
          <Link to="/contact?topic=technical">Contact ReproCare support</Link>
          <Link to="/sign-in">Back to sign-in</Link>
        </div>
      </div>
      <AuthAside />
    </div>
  );
}
