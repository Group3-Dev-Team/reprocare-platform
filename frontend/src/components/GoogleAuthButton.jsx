import { useState } from "react";
import { useFetch } from "../hooks/useFetch";
import { api, isDemoMode } from "../services/api";
import { Alert } from "./Feedback";

export const GOOGLE_ATTEMPT_KEY = "reprocare.google-attempt";

function toBase64Url(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

// make a secret verifier, send only its hash to the backend, then go to Google
export async function startGoogleAuthorization(begin, { next, intent }) {
  const verifier = toBase64Url(crypto.getRandomValues(new Uint8Array(32)));
  const hashed = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier),
  );
  const result = await begin(toBase64Url(new Uint8Array(hashed)));
  const provider = new URL(result.url);
  // only ever send the user to Google's real sign-in page
  if (
    provider.origin !== "https://accounts.google.com" ||
    provider.pathname !== "/o/oauth2/v2/auth"
  ) {
    throw new Error("Google sign-in could not start.");
  }
  sessionStorage.setItem(
    GOOGLE_ATTEMPT_KEY,
    JSON.stringify({ state: result.state, verifier, next, intent }),
  );
  window.location.assign(provider.href);
}

export default function GoogleAuthButton({
  next,
  intent = "sign-in",
  acceptTerms = false,
}) {
  const { data } = useFetch(
    (signal) => !isDemoMode && api.authCapabilities({ signal }),
    [],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  // hide the button when Google sign-in is off on the backend
  if (!data?.google || !window.crypto?.subtle) return null;

  const start = async () => {
    setError("");
    if (intent === "register" && !acceptTerms) {
      setError(
        "Accept the terms and privacy notice before creating a Google account.",
      );
      return;
    }
    setBusy(true);
    try {
      await startGoogleAuthorization(
        (challenge) =>
          api.googleStart({ challenge, intent, accept_terms: acceptTerms }),
        { next, intent },
      );
    } catch {
      setError(
        "Google sign-in could not start. Try again or use email and password.",
      );
      setBusy(false);
    }
  };

  return (
    <div className="stack" style={{ marginTop: "var(--space-4, 16px)" }}>
      {error && <Alert tone="danger">{error}</Alert>}
      <button
        type="button"
        className="btn btn-secondary btn-block"
        onClick={start}
        disabled={busy}
        aria-busy={busy}
      >
        {busy
          ? "Opening Google…"
          : intent === "register"
            ? "Create account with Google"
            : "Sign in with Google"}
      </button>
    </div>
  );
}
