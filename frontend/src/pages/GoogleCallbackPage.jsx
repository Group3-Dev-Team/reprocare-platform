import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Alert } from "../components/Feedback";
import { GOOGLE_ATTEMPT_KEY } from "../components/GoogleAuthButton";
import { AuthAside, safeNext } from "./RegisterPage";
import { dashboardHome, useAuth } from "../hooks/useAuth";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { api } from "../services/api";

// Google sends the user back here after they sign in with Google
export default function GoogleCallbackPage() {
  const [linking, setLinking] = useState(false);
  const title = linking
    ? "Connect your Google account"
    : "Complete Google sign-in";
  useDocumentTitle(title, title, { noIndex: true });
  const { completeGoogleSignIn } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  // React can run effects twice while developing, the code can only be used once
  const started = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const state = params.get("state");
    const code = params.get("code");
    const declined = params.has("error");
    // remove the code from the address bar
    window.history.replaceState(
      window.history.state,
      "",
      window.location.pathname,
    );

    const finish = async () => {
      try {
        const attempt = JSON.parse(
          sessionStorage.getItem(GOOGLE_ATTEMPT_KEY) || "null",
        );
        sessionStorage.removeItem(GOOGLE_ATTEMPT_KEY);
        const isLink = attempt?.intent === "link";
        setLinking(isLink);
        if (declined) {
          setError(
            isLink
              ? "Your Google account was not connected. You can start again."
              : "Google sign-in was not completed. You can start again.",
          );
          return;
        }
        // state must match the one we saved before going to Google
        if (
          !code ||
          !attempt ||
          !attempt.verifier ||
          !attempt.state ||
          state !== attempt.state
        ) {
          setError(
            "This Google sign-in request expired or came from a different browser tab. Start again.",
          );
          return;
        }
        const proof = { code, state, verifier: attempt.verifier };
        if (isLink) {
          await api.googleLinkExchange(proof);
          navigate("/dashboard/account", { replace: true });
          return;
        }
        const account = await completeGoogleSignIn(proof);
        const next = safeNext(attempt.next);
        navigate(
          account.role === "patient" && next ? next : dashboardHome(account),
          { replace: true },
        );
      } catch (err) {
        setError(
          err?.status
            ? err.message
            : "Google sign-in could not be completed. Start again.",
        );
      }
    };

    finish();
  }, [completeGoogleSignIn, navigate, params]);

  return (
    <div className="auth-page">
      <div className="auth-card stack">
        <h1>{title}</h1>
        {error ? (
          <>
            <Alert tone="danger">{error}</Alert>
            <Link
              to={linking ? "/dashboard/account" : "/sign-in"}
              className="btn btn-secondary"
            >
              {linking ? "Back to account settings" : "Back to sign-in"}
            </Link>
          </>
        ) : (
          <p role="status">Verifying your Google account…</p>
        )}
      </div>
      <AuthAside />
    </div>
  );
}
