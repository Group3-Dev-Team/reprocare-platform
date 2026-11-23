import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { dashboardHome, useAuth } from "../hooks/useAuth";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { PasswordInput, TextInput } from "../components/Forms";
import { Alert } from "../components/Feedback";
import GoogleAuthButton from "../components/GoogleAuthButton";
import { useToast } from "../components/Toast";
import { AuthAside, AuthSwitch, safeNext } from "./RegisterPage";

export default function SignInPage() {
  useDocumentTitle(
    "Sign in",
    "Sign in to your ReproCare patient or healthcare staff workspace.",
  );
  const { user, signIn } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get("next"));

  // patients go back to the page that sent them here, staff and admins go to their dashboard
  const destination = (account) =>
    next && (account.role === "patient" || /^\/dashboard(?:[/?#]|$)/.test(next))
      ? next
      : dashboardHome(account);

  if (user) return <Navigate to={destination(user)} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    const found = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim()))
      found.email = "Enter the email address you registered with.";
    if (!form.password) found.password = "Enter your password.";
    else if (form.password.length > 128)
      found.password = "Use 128 characters or fewer.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setError(null);
    try {
      const signedIn = await signIn(form.email.trim(), form.password);
      toast(`Welcome back, ${signedIn.full_name.split(" ")[0]}.`);
      navigate(destination(signedIn), { replace: true });
    } catch (err) {
      setError(
        err.status >= 500
          ? "ReproCare could not complete sign-in. Please try again shortly."
          : err.message,
      );
      setErrors(err.fields || {});
      // wrong details: clear the password box (we don't say if it was the email or the password)
      if (err.status === 401) setForm((f) => ({ ...f, password: "" }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <AuthSwitch active="sign-in" next={next} />
        <h1>Welcome back</h1>
        <p className="muted">
          Patients and healthcare staff sign in here. Your account opens the
          workspace for your role.
        </p>
        <form className="stack" onSubmit={submit} noValidate>
          {error && <Alert tone="danger">{error}</Alert>}
          <TextInput
            label="Email address"
            type="email"
            inputMode="email"
            autoComplete="email"
            autoFocus
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            error={errors.email}
            required
          />
          <PasswordInput
            label="Password"
            autoComplete="current-password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            error={errors.password}
            required
          />
          <div className="auth-row">
            <Link to="/forgot-password" className="small">
              Forgot password?
            </Link>
          </div>
          <button
            className="btn btn-primary btn-lg btn-block"
            disabled={busy}
            aria-busy={busy}
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <GoogleAuthButton next={next} />
        <div className="auth-foot">
          <p className="small">
            New to ReproCare?{" "}
            <Link
              to={`/register${next ? `?next=${encodeURIComponent(next)}` : ""}`}
            >
              Create a free account
            </Link>
          </p>
          <p className="small muted">
            Facility staff and administrators sign in with the account their
            administrator created.
          </p>
        </div>
      </div>
      <AuthAside />
    </div>
  );
}
