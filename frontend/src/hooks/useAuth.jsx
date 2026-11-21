import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, getToken, setToken } from '../services/api';

const AuthContext = createContext(null);

/** Keeps the signed-in user for the whole app. Wrap the app in <AuthProvider>. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getToken()));

  const [sessionError, setSessionError] = useState(null);
  const activeCheck = useRef(null);

  const updateSession = useCallback((token, account) => {
    activeCheck.current?.abort();
    activeCheck.current = null;
    setToken(token);
    setUser(account);
    setSessionError(null);
    setLoading(false);
  }, []);

  const verifySession = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    activeCheck.current?.abort();
    const controller = new AbortController();
    activeCheck.current = controller;
    setLoading(true);
    setSessionError(null);

    try {
      const verified = await api.me({ signal: controller.signal });
      if (!controller.signal.aborted) setUser(verified);
    } catch (error) {
      if (controller.signal.aborted) return;
      if (error.status === 401) updateSession(null, null);
      else setSessionError({ message: 'We could not verify your ReproCare session. Please try again.' });
    } finally {
      if (activeCheck.current === controller) {
        activeCheck.current = null;
        setLoading(false);
      }
    }
  }, [updateSession]);

  useEffect(() => {
    verifySession();
    return () => activeCheck.current?.abort();
  }, [verifySession]);

  useEffect(() => {
    const onSignedOut = () => updateSession(null, null);
    window.addEventListener('reprocare:signed-out', onSignedOut);
    return () => window.removeEventListener('reprocare:signed-out', onSignedOut);
  }, [updateSession]);

  const signIn = useCallback(async (email, password) => {
    const { token, user: signedIn } = await api.login({ email, password });
    updateSession(token, signedIn);
    return signedIn;
  }, [updateSession]);

  const register = useCallback(async (details) => {
    const { token, user: created } = await api.register(details);
    updateSession(token, created);
    return created;
  }, [updateSession]);

  const completeGoogleSignIn = useCallback(async (proof) => {
    const { token, user: account } = await api.googleExchange(proof);
    updateSession(token, account);
    return account;
  }, [updateSession]);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Clear the local session even when the server is unreachable.
    }
    updateSession(null, null);
  }, [updateSession]);

  const value = useMemo(() => (
    { user, loading, sessionError, verifySession, signIn, register, completeGoogleSignIn, signOut, setUser }
  ), [user, loading, sessionError, verifySession, signIn, register, completeGoogleSignIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

/** Where each role lands after signing in. */
export function dashboardHome(user) {
  if (!user) return '/sign-in';
  return { patient: '/dashboard', facility_staff: '/dashboard/facility', admin: '/dashboard/admin' }[user.role] || '/';
}
