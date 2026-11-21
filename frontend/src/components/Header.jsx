import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, NavLink, useLocation } from 'react-router-dom';
import {
  ArrowRight, BookOpen, Bot, Building2, CalendarDays, ChevronDown, ClipboardList, FlaskConical, GitCompareArrows, Heart,
  Info, LayoutDashboard, LogOut, MapPin, Menu, MessageCircle, Settings, ShieldCheck, Stethoscope, UserRound, X,
} from 'lucide-react';
import { publicNav, roleLabels } from '../data/navigation';
import { dashboardHome, useAuth } from '../hooks/useAuth';
import { useDialogFocus } from '../hooks/useDialogFocus';
import { Logo } from './Logo';
import { ThemeToggle } from './ThemeToggle';
import { UserMenu, useSignOut } from './UserMenu';

const itemIcons = {
  '/find-care/facilities': Building2,
  '/find-care/specialists': Stethoscope,
  '/find-care/laboratories': FlaskConical,
  '/find-care/insurance': ShieldCheck,
  '/find-care/map': MapPin,
  '/compare': GitCompareArrows,
  '/health-community/programmes': CalendarDays,
  '/health-library': BookOpen,
  '/assistant': Bot,
  '/patient-experiences': Heart,
  '/about': Info,
  '/how-it-works': ClipboardList,
  '/trust': ShieldCheck,
  '/contact': MessageCircle,
};

function NavigationLinks({ pathname, open, setOpen, followLink, isDrawer }) {
  const id = useId();

  const groupActive = (group) => group.items.some(({ to }) => pathname === to || pathname.startsWith(to + '/'))
    || (group.label === 'Find Care' && pathname.startsWith('/facilities/'))
    || (group.label === 'Health & Community' && /^(\/health-community\/|\/programmes\/)/.test(pathname));

  return (
    <ul className="main-nav-list">
      <li>
        <NavLink to="/" end className="nav-link" onClick={() => followLink('/', isDrawer)}>Home</NavLink>
      </li>
      {publicNav.map((group, index) => {
        const expanded = open === group.label;
        const panelId = id + '-group-' + index;
        return (
          <li
            key={group.label}
            className="nav-group"
            onBlur={(event) => {
              if (!isDrawer && expanded && !event.currentTarget.contains(event.relatedTarget)) setOpen(null);
            }}
          >
            <button
              type="button"
              className={'nav-link nav-trigger' + (groupActive(group) ? ' active' : '')}
              aria-expanded={expanded}
              aria-controls={panelId}
              onClick={() => setOpen(expanded ? null : group.label)}
            >
              {group.label}
              <ChevronDown size={16} aria-hidden="true" />
            </button>
            <div id={panelId} className={'dropdown' + (expanded ? ' is-open' : '')} hidden={!expanded}>
              <ul>
                {group.items.map((item) => {
                  const Icon = itemIcons[item.to];
                  return (
                    <li key={item.to}>
                      <NavLink to={item.to} className="dropdown-link" onClick={() => followLink(item.to, isDrawer)}>
                        {Icon && <span className="dropdown-icon"><Icon size={18} aria-hidden="true" /></span>}
                        <span className="dropdown-copy">
                          <span className="dropdown-label">{item.label}</span>
                          <span className="dropdown-note">{item.note}</span>
                        </span>
                      </NavLink>
                    </li>
                  );
                })}
              </ul>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/** Sticky public navigation with disclosure menus and a modal mobile drawer. */
export function Header() {
  const [open, setOpen] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileGroup, setMobileGroup] = useState(null);
  const { user } = useAuth();
  const doSignOut = useSignOut();
  const { pathname, search, hash } = useLocation();
  const navRef = useRef(null);
  const drawerRef = useRef(null);
  const mobileTrigger = useRef(null);
  const closeMobile = useCallback(() => {
    setMobileOpen(false);
    setMobileGroup(null);
  }, []);

  useDialogFocus(drawerRef, mobileOpen, closeMobile, {
    initialFocus: '[data-initial-focus]',
    returnFocus: mobileTrigger,
  });

  useEffect(() => {
    setOpen(null);
    closeMobile();
  }, [pathname, search, hash, closeMobile]);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (!navRef.current?.contains(event.target)) setOpen(null);
    };
    const onKeyDown = (event) => {
      if (event.key !== 'Escape') return;
      const trigger = navRef.current?.querySelector('.nav-trigger[aria-expanded="true"]');
      if (trigger) {
        event.preventDefault();
        setOpen(null);
        trigger.focus();
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (!mobileOpen) return undefined;
    const media = window.matchMedia('(min-width: 1081px)');
    const closeOnDesktop = (event) => {
      if (event.matches) closeMobile();
    };
    media.addEventListener('change', closeOnDesktop);
    return () => media.removeEventListener('change', closeOnDesktop);
  }, [mobileOpen, closeMobile]);

  const followLink = (to, isDrawer) => {
    setOpen(null);
    closeMobile();
    if (pathname + search + hash === to) {
      if (!isDrawer) document.getElementById('main')?.focus({ preventScroll: true });
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  };

  const accountLinks = (isDrawer = false) => (
    <>
      <Link to="/sign-in" className="btn btn-ghost btn-sm" onClick={() => followLink('/sign-in', isDrawer)}>Sign in</Link>
      <Link to="/register" className="btn btn-primary btn-sm" onClick={() => followLink('/register', isDrawer)}>
        Create account
        <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </>
  );

  return (
    <header className="site-header">
      <div className="container site-header-inner">
        <Logo />
        <nav className="main-nav" aria-label="Main" ref={navRef}>
          <NavigationLinks pathname={pathname} open={open} setOpen={setOpen} followLink={followLink} />
          <div className="nav-actions"><ThemeToggle />{user ? <UserMenu /> : accountLinks()}</div>
        </nav>
        <div className="header-quick">
          <ThemeToggle />
          {user ? <UserMenu /> : (
            <Link to="/sign-in" className="btn btn-secondary btn-sm header-signin" onClick={() => followLink('/sign-in', false)}>
              <UserRound size={16} aria-hidden="true" /> Sign in
            </Link>
          )}
        </div>
        <button
          type="button"
          ref={mobileTrigger}
          className="icon-btn menu-toggle"
          aria-controls={mobileOpen ? 'mobile-navigation' : undefined}
          aria-expanded={mobileOpen}
          aria-haspopup="dialog"
          aria-label="Open menu"
          onClick={() => setMobileOpen(true)}
        >
          <Menu size={22} aria-hidden="true" />
        </button>
      </div>
      {mobileOpen && createPortal(
        <div className="mobile-nav-backdrop" onClick={(event) => event.target === event.currentTarget && closeMobile()}>
          <section className="mobile-nav-drawer" role="dialog" aria-modal="true" aria-labelledby="mobile-navigation-title" id="mobile-navigation" ref={drawerRef}>
            <div className="mobile-nav-head">
              <h2 id="mobile-navigation-title">Menu</h2>
              <button type="button" className="icon-btn mobile-nav-close" aria-label="Close menu" data-initial-focus onClick={closeMobile}>
                <X size={22} aria-hidden="true" />
              </button>
            </div>
            <nav aria-label="Main">
              <NavigationLinks pathname={pathname} open={mobileGroup} setOpen={setMobileGroup} followLink={followLink} isDrawer />
            </nav>
            <div className="nav-actions">
              {user ? (
                <div className="nav-account">
                  <p className="nav-account-label">Signed in as {user.full_name}</p>
                  <Link to={dashboardHome(user)} className="btn btn-secondary" onClick={closeMobile}>
                    <LayoutDashboard size={16} aria-hidden="true" />
                    {user.role === 'patient' ? 'My ReproCare' : roleLabels[user.role]}
                  </Link>
                  <Link to="/dashboard/account" className="btn btn-ghost" onClick={closeMobile}>
                    <Settings size={16} aria-hidden="true" /> Account settings
                  </Link>
                  <button type="button" className="btn btn-ghost" onClick={() => { closeMobile(); doSignOut(); }}>
                    <LogOut size={16} aria-hidden="true" /> Sign out
                  </button>
                </div>
              ) : accountLinks(true)}
            </div>
          </section>
        </div>,
        document.body,
      )}
    </header>
  );
}
