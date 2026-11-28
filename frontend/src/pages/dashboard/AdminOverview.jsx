import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarClock,
  Database,
  Inbox,
  Megaphone,
  Star,
  Users,
} from "lucide-react";
import { api } from "../../services/api";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { DashboardHeader, StatCard } from "../../components/DashboardParts";
import { ErrorState, LoadingState } from "../../components/Feedback";

export default function AdminOverview() {
  useDocumentTitle("Platform operations");
  const o = useFetch(() => api.adminOverview(), []);
  if (o.error) return <ErrorState error={o.error} onRetry={o.reload} />;
  if (!o.data) return <LoadingState rows={2} />;
  const d = o.data;
  return (
    <>
      <DashboardHeader
        title="Platform operations"
        description="Work waiting for an administrator, and the state of the directory."
      />
      <h2 className="dash-subhead">Needs attention</h2>
      <div className="stat-grid">
        <StatCard
          icon={Star}
          tone="amber"
          label="Reviews awaiting moderation"
          value={d.reviews_pending}
          to="/dashboard/admin/reviews"
        />
        <StatCard
          icon={Inbox}
          tone="rose"
          label="New contact messages"
          value={d.contact_new}
          to="/dashboard/admin/messages"
        />
        <StatCard
          icon={CalendarClock}
          label="Requests awaiting facilities"
          value={d.appointments_open}
        />
      </div>
      <h2 className="dash-subhead">Directory and community</h2>
      <div className="stat-grid">
        <StatCard
          icon={Database}
          label="Facilities listed"
          value={d.facilities}
          to="/dashboard/admin/imports"
        />
        <StatCard
          icon={Megaphone}
          tone="green"
          label="Upcoming programmes"
          value={d.programs_upcoming}
          to="/dashboard/admin/programmes"
        />
        <StatCard
          icon={Users}
          label="Patient accounts"
          value={d.users.patient || 0}
          to="/dashboard/admin/users"
        />
        <StatCard
          icon={Users}
          tone="green"
          label="Facility staff accounts"
          value={d.users.facility_staff || 0}
          to="/dashboard/admin/users"
        />
      </div>
      <h2 className="dash-subhead">Quick actions</h2>
      <div className="quick-actions">
        {[
          {
            to: "/dashboard/admin/reviews",
            icon: Star,
            title: "Moderate reviews",
            note: "Publish or reject patient experiences",
          },
          {
            to: "/dashboard/admin/programmes",
            icon: Megaphone,
            title: "Publish a programme",
            note: "Add an outreach or screening event",
          },
          {
            to: "/dashboard/admin/imports",
            icon: Database,
            title: "Import facility data",
            note: "Load a validated batch of listings",
          },
          {
            to: "/dashboard/admin/users",
            icon: Users,
            title: "Manage accounts",
            note: "Create staff accounts, deactivate users",
          },
        ].map(({ to, icon: Icon, title, note }) => (
          <Link key={to} to={to} className="quick-action">
            <span className="stat-icon stat-blue" aria-hidden="true">
              <Icon size={18} />
            </span>
            <span>
              <strong>{title}</strong>
              <span className="small muted">{note}</span>
            </span>
            <ArrowRight
              size={16}
              aria-hidden="true"
              className="quick-action-arrow"
            />
          </Link>
        ))}
      </div>
    </>
  );
}
