import { useState } from "react";
import { api } from "../../services/api";
import { useAuth } from "../../hooks/useAuth";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { roleLabels } from "../../data/navigation";
import { DashboardHeader } from "../../components/DashboardParts";
import {
  PasswordInput,
  StrengthMeter,
  TextInput,
} from "../../components/Forms";
import { Alert } from "../../components/Feedback";
import { GoogleLinkPanel } from "../../components/GoogleLinkPanel";
import { useToast } from "../../components/Toast";
import { useSignOut } from "../../components/UserMenu";
import { setToken } from "../../services/api";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";

export default function AccountSettings() {
  useDocumentTitle("Account settings");
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [profile, setProfile] = useState({
    full_name: user.full_name,
    phone: user.phone || "",
  });
  const [pw, setPw] = useState({
    current_password: "",
    new_password: "",
    confirm: "",
  });
  const [errors, setErrors] = useState({});
  const [pwError, setPwError] = useState(null);
  const [sessionsError, setSessionsError] = useState(null);
  const [busy, setBusy] = useState(null); // 'profile' | 'password' | 'everywhere'
  const doSignOut = useSignOut();
  const navigate = useNavigate();
  // save button only works when something changed
  const dirty =
    profile.full_name !== user.full_name ||
    profile.phone !== (user.phone || "");

  const saveProfile = async (e) => {
    e.preventDefault();
    if (profile.full_name.trim().length < 2)
      return setErrors({ full_name: "Enter your full name." });
    setErrors({});
    setBusy("profile");
    try {
      setUser(
        await api.updateMe({
          full_name: profile.full_name.trim(),
          phone: profile.phone.trim() || null,
        }),
      );
      toast("Profile updated");
    } catch (err) {
      setErrors(err.fields || {});
      toast(err.message, "error");
    } finally {
      setBusy(null);
    }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setPwError(null);
    if (!pw.current_password) return setPwError("Enter your current password.");
    if (
      pw.new_password.length < 8 ||
      !/\d/.test(pw.new_password) ||
      !/[a-z]/i.test(pw.new_password)
    )
      return setPwError(
        "Use at least 8 characters, including letters and a number.",
      );
    if (pw.new_password !== pw.confirm)
      return setPwError("The new passwords do not match.");
    setBusy("password");
    try {
      await api.changePassword({
        current_password: pw.current_password,
        new_password: pw.new_password,
      });
      setPw({ current_password: "", new_password: "", confirm: "" });
      toast("Password changed. Other devices have been signed out.");
    } catch (err) {
      setPwError(err.fields?.new_password || err.message);
    } finally {
      setBusy(null);
    }
  };

  const signOutEverywhere = async () => {
    setBusy("everywhere");
    setSessionsError(null);
    try {
      await api.logoutAll();
      setToken(null);
      window.dispatchEvent(new Event("reprocare:signed-out"));
      navigate("/sign-in", { replace: true });
      toast("Signed out on all devices.");
    } catch {
      setSessionsError(
        "ReproCare could not confirm that other sessions ended. Try again, or sign out on this device.",
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <DashboardHeader
        title="Account settings"
        description="Your contact details, password and signed-in devices."
      />
      <div className="dash-grid two">
        <form className="panel stack" onSubmit={saveProfile} noValidate>
          <h2>Profile</h2>
          <TextInput
            label="Full name"
            value={profile.full_name}
            onChange={(e) =>
              setProfile({ ...profile, full_name: e.target.value })
            }
            error={errors.full_name}
            required
          />
          <TextInput
            label="Email address"
            value={user.email}
            disabled
            hint="Contact support to change your email address."
          />
          <TextInput
            label="Phone number"
            type="tel"
            value={profile.phone}
            onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
            hint="Used to pre-fill appointment and registration forms."
          />
          <p className="small muted">
            Account type: {roleLabels[user.role]}
            {user.facility ? `, ${user.facility.name}` : ""}
          </p>
          <button
            className="btn btn-primary"
            disabled={!dirty || busy === "profile"}
          >
            {busy === "profile" ? "Saving…" : "Save changes"}
          </button>
        </form>
        <form className="panel stack" onSubmit={changePassword} noValidate>
          <h2>Change password</h2>
          {pwError && <Alert tone="danger">{pwError}</Alert>}
          <PasswordInput
            label="Current password"
            autoComplete="current-password"
            value={pw.current_password}
            onChange={(e) => setPw({ ...pw, current_password: e.target.value })}
            required
          />
          <div>
            <PasswordInput
              label="New password"
              autoComplete="new-password"
              value={pw.new_password}
              onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
              hint="At least 8 characters, including a number."
              required
            />
            <StrengthMeter value={pw.new_password} />
          </div>
          <PasswordInput
            label="Confirm new password"
            autoComplete="new-password"
            value={pw.confirm}
            onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
            required
          />
          <button className="btn btn-secondary" disabled={busy === "password"}>
            {busy === "password" ? "Updating…" : "Change password"}
          </button>
        </form>
      </div>
      <section className="panel stack" style={{ marginTop: 20 }}>
        <h2 className="row" style={{ gap: 8 }}>
          <ShieldCheck size={20} aria-hidden="true" /> Sessions
        </h2>
        {sessionsError && <Alert tone="danger">{sessionsError}</Alert>}
        <p className="small muted">
          Signed in on a shared or lost device? Sign out everywhere and sign in
          again on this one.
        </p>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <button className="btn btn-ghost" onClick={doSignOut}>
            <LogOut size={16} aria-hidden="true" /> Sign out
          </button>
          <button
            className="btn btn-danger"
            onClick={signOutEverywhere}
            disabled={busy === "everywhere"}
          >
            {busy === "everywhere" ? "Signing out…" : "Sign out on all devices"}
          </button>
        </div>
      </section>
      <GoogleLinkPanel />
      <section className="panel stack" style={{ marginTop: 20 }}>
        <h2>Account privacy</h2>
        <p>
          To request a copy of your data, contact ReproCare support so they can
          verify the request.
        </p>
        <Link
          to="/contact?topic=privacy"
          state={{ draft: "Account privacy request" }}
        >
          Open the privacy request form
        </Link>
      </section>
      {/* only patients can close their own account */}
      {user.role === "patient" ? (
        <CloseAccount user={user} />
      ) : (
        <section className="panel stack" style={{ marginTop: 20 }}>
          <h2>Close account</h2>
          <p className="small muted">
            Staff and administrator accounts are closed by a ReproCare
            administrator. <Link to="/contact?topic=privacy">Contact us</Link>{" "}
            to close this account.
          </p>
        </section>
      )}
    </>
  );
}

function CloseAccount({ user }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ confirm_email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();

  const submit = async (e) => {
    e.preventDefault();
    if (form.confirm_email.trim().toLowerCase() !== user.email.toLowerCase())
      return setError("Type the email address for this account to confirm.");
    setBusy(true);
    setError(null);
    try {
      await api.closeAccount({
        confirm_email: form.confirm_email.trim(),
        password: form.password,
      });
      setToken(null);
      window.dispatchEvent(new Event("reprocare:signed-out"));
      navigate("/", { replace: true });
      toast("Your account has been closed.");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <section
      className="panel stack account-close"
      style={{ marginTop: 20 }}
      aria-labelledby="close-account-heading"
    >
      <h2 id="close-account-heading">Close account</h2>
      <p className="small">
        Closing your account signs you out everywhere and cannot be undone. Open
        appointment requests and programme registrations are cancelled, and
        saved facilities and notifications are deleted. Facilities keep a record
        of past request dates without your name, phone or notes. Published
        reviews stay under “Former ReproCare user”; reviews awaiting moderation
        are deleted.
      </p>
      {!open ? (
        <div>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => setOpen(true)}
          >
            Close my account
          </button>
        </div>
      ) : (
        <form className="stack" onSubmit={submit} noValidate>
          {error && <Alert tone="danger">{error}</Alert>}
          <TextInput
            label="Type your email address to confirm"
            type="email"
            autoComplete="off"
            value={form.confirm_email}
            onChange={(e) =>
              setForm({ ...form, confirm_email: e.target.value })
            }
            required
          />
          <PasswordInput
            label="Password"
            autoComplete="current-password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            hint="Leave blank only if you sign in with Google and have never set a password."
          />
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <button className="btn btn-danger" disabled={busy}>
              {busy ? "Closing…" : "Permanently close account"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setOpen(false);
                setError(null);
              }}
              disabled={busy}
            >
              Keep my account
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
