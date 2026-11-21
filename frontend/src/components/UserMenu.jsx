import { facilityDisplayName } from '../data/facilityNames';
import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Bell, ChevronDown, Globe, LayoutDashboard, LogOut, Settings } from 'lucide-react';
import { roleLabels } from '../data/navigation';
import { dashboardHome, useAuth } from '../hooks/useAuth';
import { useToast } from './Toast';

export function initials(name = '') {
  return (
    name
      .split(' ')
      .filter(Boolean)
      .map((p) => p[0])
      .slice(0, 2)
      .join('')
      .toUpperCase() || '?'
  );
}

/** Signs out, confirms with a toast and returns to the homepage. Shared by every sign-out control. */
export function useSignOut() {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  return async () => {
    await signOut();
    navigate('/', { replace: true });
    toast('You have signed out.');
  };
}

/**
 * Avatar button with an account dropdown. Used in the public header and the dashboard top bar.
 * props: unread (notification count), inDashboard (shows "Back to ReproCare" instead of "Dashboard")
 */
export function UserMenu({ unread = 0, inDashboard = false }) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const { pathname } = useLocation();
  const doSignOut = useSignOut();

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => !ref.current?.contains(e.target) && setOpen(false);
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!user) return null;
  const firstName = user.full_name.split(' ')[0];

  return (
    <div className="user-menu" ref={ref}>
      <button className="user-menu-trigger" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="avatar avatar-sm" aria-hidden="true">
          {initials(user.full_name)}
        </span>
        <span className="user-menu-name">{firstName}</span>
        <ChevronDown size={16} aria-hidden="true" className="user-menu-chevron" />
        <span className="sr-only">Account menu</span>
      </button>
      {open && (
        <div className="user-menu-panel" role="menu">
          <div className="user-menu-head">
            <span className="avatar" aria-hidden="true">
              {initials(user.full_name)}
            </span>
            <div>
              <strong>{user.full_name}</strong>
              <span>{user.email}</span>
              <span className="user-menu-role">{user.facility ? facilityDisplayName(user.facility) : roleLabels[user.role]}</span>
            </div>
          </div>
          <div className="user-menu-items">
            {inDashboard ? (
              <Link role="menuitem" to="/" className="user-menu-item">
                <Globe size={17} aria-hidden="true" /> Back to ReproCare
              </Link>
            ) : (
              <Link role="menuitem" to={dashboardHome(user)} className="user-menu-item">
                <LayoutDashboard size={17} aria-hidden="true" /> {user.role === 'patient' ? 'My ReproCare' : 'Dashboard'}
              </Link>
            )}
            <Link role="menuitem" to="/dashboard/notifications" className="user-menu-item">
              <Bell size={17} aria-hidden="true" /> Notifications
              {unread > 0 && <span className="user-menu-count">{unread}</span>}
            </Link>
            <Link role="menuitem" to="/dashboard/account" className="user-menu-item">
              <Settings size={17} aria-hidden="true" /> Account settings
            </Link>
          </div>
          <div className="user-menu-items user-menu-foot">
            <button role="menuitem" className="user-menu-item is-danger" onClick={doSignOut}>
              <LogOut size={17} aria-hidden="true" /> Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
