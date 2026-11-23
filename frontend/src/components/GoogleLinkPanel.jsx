import { useState } from "react";
import { useFetch } from "../hooks/useFetch";
import { api, isDemoMode } from "../services/api";
import { Alert } from "./Feedback";
import { PasswordInput } from "./Forms";
import { startGoogleAuthorization } from "./GoogleAuthButton";

// box in Account settings for connecting a Google account
export function GoogleLinkPanel() {
  const { data } = useFetch(
    (signal) => !isDemoMode && api.googleLinkStatus({ signal }),
    [],
  );
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // hidden when Google sign-in is off
  if (!data?.available) return null;
  if (data.linked) {
    return (
      <section className="panel stack" style={{ marginTop: 20 }}>
        <h2>Google sign-in</h2>
        <p>Your Google account is connected to ReproCare.</p>
      </section>
    );
  }
  if (!window.crypto?.subtle) return null;

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    // clear the password box straight away
    setPassword("");
    try {
      await startGoogleAuthorization(
        (challenge) =>
          api.googleLinkStart({ challenge, current_password: password }),
        { intent: "link" },
      );
    } catch (err) {
      setError(
        err?.status
          ? err.message
          : "We could not connect to Google. Try again.",
      );
      setBusy(false);
    }
  };

  return (
    <section className="panel stack" style={{ marginTop: 20 }}>
      <h2>Google sign-in</h2>
      <p>
        Connect a Google account that uses the same email address as your
        ReproCare account.
      </p>
      <form className="stack" onSubmit={submit}>
        {error && <Alert tone="danger">{error}</Alert>}
        <PasswordInput
          label="Confirm your ReproCare password"
          value={password}
          autoComplete="current-password"
          onChange={(event) => setPassword(event.target.value)}
          maxLength={128}
          disabled={busy}
          required
        />
        <button
          type="submit"
          className="btn btn-secondary"
          disabled={busy}
          aria-busy={busy}
        >
          {busy ? "Opening Google…" : "Connect Google account"}
        </button>
      </form>
    </section>
  );
}
