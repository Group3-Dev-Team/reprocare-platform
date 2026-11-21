import { useEffect, useRef, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Bell, Menu, Search } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { api } from '../services/api';
import { dashboardNav } from '../data/navigation';
import { Sidebar } from '../components/Sidebar';
import { ThemeToggle } from '../components/ThemeToggle';
import { UserMenu } from '../components/UserMenu';

/** The sidebar entry that matches the current page, for the top-bar title. */
function currentSection(role, pathname) {
  const items = dashboardNav[role] || [];
  const exact = items.find((i) => i.to === pathname);
  if (exact) return exact.label;
  const prefix = items.filter((i) => !i.end && pathname.startsWith(i.to)).sort((a, b) => b.to.length - a.to.length)[0];
  return prefix?.label || 'Overview';
}

/** Signed-in workspace: sidebar on the left, compact top bar, page content on the right. */
export function DashboardLayout() {
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const drawer = useRef(null);
  const opener = useRef(null);
  const scrim = useRef(null);

  useDialogFocus(drawer, open, () => setOpen(false), {
    initialFocus: '.sidebar-close',
    returnFocus: opener,
    allowOutside: scrim,
  });

  useEffect(() => {
    window.scrollTo(0, 0);
    setOpen(false);
    api
      .notifications()
      .then((n) => setUnread(n.unread))
      .catch(() => {});
  }, [pathname]);

  useEffect(() => {
    if (!open) return undefined;
    const desktop = window.matchMedia('(min-width: 961px)');
    const sync = () => {
      if (desktop.matches) setOpen(false);
    };
    desktop.addEventListener('change', sync);
    return () => desktop.removeEventListener('change', sync);
  }, [open]);

  return (
    <div className="dashboard-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Sidebar user={user} unread={unread} open={open} drawerRef={drawer} onNavigate={() => setOpen(false)} onClose={() => setOpen(false)} />
      {open && <div ref={scrim} className="sidebar-scrim" onClick={() => setOpen(false)} />}
      <div className="dashboard-main">
        <div className="topbar">
          <button ref={opener} className="icon-btn topbar-menu" aria-label="Open dashboard menu" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}>
            <Menu size={20} />
          </button>
          <p className="topbar-title">{currentSection(user.role, pathname)}</p>
          <div className="topbar-actions">
            <ThemeToggle />
            <Link to="/find-care/facilities" className="btn btn-ghost btn-sm topbar-find">
              <Search size={16} aria-hidden="true" />
              <span>Find care</span>
            </Link>
            <Link to="/dashboard/notifications" className="icon-btn topbar-bell" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}>
              <Bell size={18} />
              {unread > 0 && <span className="dot" />}
            </Link>
            <UserMenu unread={unread} inDashboard />
          </div>
        </div>
        <main id="main" tabIndex={-1} className="dashboard-content">
          <Outlet context={{ setUnread }} />
        </main>
      </div>
    </div>
  );
}
