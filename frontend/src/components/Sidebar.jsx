import { facilityDisplayName } from '../data/facilityNames';
import { NavLink } from 'react-router-dom';
import { ArrowLeft, Bell, Building2, CalendarDays, Database, Heart, Home, Inbox, LogOut, Megaphone, Settings, Star, Ticket, Users, X } from 'lucide-react';
import { dashboardNav, roleLabels } from '../data/navigation';
import { Logo } from './Logo';
import { initials, useSignOut } from './UserMenu';

const icons = { home: Home, calendar: CalendarDays, heart: Heart, ticket: Ticket, star: Star, bell: Bell, settings: Settings, building: Building2, megaphone: Megaphone, inbox: Inbox, users: Users, database: Database };

export function Sidebar({ user, unread, open, drawerRef, onNavigate, onClose }) {
  const doSignOut = useSignOut();
  return (
    <aside
      ref={drawerRef}
      className={`sidebar ${open ? 'is-open' : ''}`}
      aria-label="Dashboard"
      role={open ? 'dialog' : undefined}
      aria-modal={open || undefined}
      tabIndex={open ? -1 : undefined}
    >
      <div className="sidebar-brand">
        <Logo />
        <button className="icon-btn sidebar-close" aria-label="Close dashboard menu" onClick={onClose}>
          <X size={18} />
        </button>
      </div>
      <div className="sidebar-user">
        <span className="avatar" aria-hidden="true">
          {initials(user.full_name)}
        </span>
        <div>
          <strong>{user.full_name}</strong>
          <span>{user.facility ? facilityDisplayName(user.facility) : roleLabels[user.role]}</span>
        </div>
      </div>
      <nav>
        <ul className="sidebar-nav">
          {dashboardNav[user.role].map((item) => {
            const Icon = icons[item.icon];
            return (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className="sidebar-link" onClick={onNavigate}>
                  <Icon size={18} aria-hidden="true" />
                  <span>{item.label}</span>
                  {item.badge === 'unread' && unread > 0 && (
                    <span className="sidebar-count" aria-label={`${unread} unread`}>
                      {unread}
                    </span>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="sidebar-foot">
        <NavLink to="/" className="sidebar-link" onClick={onNavigate}>
          <ArrowLeft size={18} aria-hidden="true" />
          <span>Back to ReproCare</span>
        </NavLink>
        <button className="sidebar-link sidebar-signout" onClick={doSignOut}>
          <LogOut size={18} aria-hidden="true" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
