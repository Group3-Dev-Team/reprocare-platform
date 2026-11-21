import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { dashboardHome, useAuth } from '../hooks/useAuth';
import { ErrorState, LoadingState } from './Feedback';

/**
 * Shows child routes only to signed-in users with one of the allowed roles.
 * This is a convenience for the interface; the backend enforces the same rules on every request.
 */
export function ProtectedRoute({ roles }) {
  const { user, loading, sessionError, verifySession } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <div className="container" style={{ padding: '48px 0' }}>
        <LoadingState rows={2} />
      </div>
    );
  }
  if (sessionError) {
    return <div className="container section"><ErrorState error={sessionError} onRetry={verifySession} /></div>;
  }
  if (!user) return <Navigate to={`/sign-in?next=${encodeURIComponent(location.pathname + location.search + location.hash)}`} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={dashboardHome(user)} replace />;
  return <Outlet />;
}
