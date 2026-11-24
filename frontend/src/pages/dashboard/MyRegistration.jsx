import { Link } from "react-router-dom";
import { Ticket } from "lucide-react";
import { api } from "../../services/api";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { formatDate, registrationStatus } from "../../data/labels";
import { DashboardHeader } from "../../components/DashboardParts";
import { DemoLabel, StatusBadge } from "../../components/Badges";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/Feedback";
import { useToast } from "../../components/Toast";
import { ConfirmButton } from "../../components/ConfirmButton";

export default function MyRegistrations() {
  useDocumentTitle("Programme registrations");
  const toast = useToast();
  const result = useFetch(() => api.myRegistrations(), []);
  const cancel = async (r) => {
    try {
      await api.cancelRegistration(r.reference);
      toast("Registration cancelled. Your place has been released.");
      result.reload();
    } catch (e) {
      toast(e.message, "error");
    }
  };
  return (
    <>
      <DashboardHeader
        title="Programme registrations"
        description="Show your reference at the venue. Registration holds a place; it is not a record of any health service."
        actions={
          <Link className="btn btn-primary" to="/health-community/programmes">
            Browse programmes
          </Link>
        }
      />
      {result.loading && <LoadingState rows={2} height={90} />}
      {result.error && (
        <ErrorState error={result.error} onRetry={result.reload} />
      )}
      {result.data?.length === 0 && (
        <EmptyState
          icon={<Ticket size={24} />}
          title="No registrations yet"
          action={
            <Link className="btn btn-primary" to="/health-community/free-care">
              Find free & subsidised care
            </Link>
          }
        />
      )}
      {result.data?.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Programme</th>
                <th>Date</th>
                <th>Reference</th>
                <th>Status</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.data.map((r) => (
                <tr key={r.reference}>
                  <td>
                    <Link to={`/programmes/${r.program.slug}`}>
                      <strong>{r.program.title}</strong>
                    </Link>
                    <div className="small muted">{r.program.venue}</div>
                    {r.program.is_demo && <DemoLabel />}
                  </td>
                  <td>
                    {formatDate(r.program.start_date)}
                    <div className="small muted">
                      {r.program.start_time} – {r.program.end_time}
                    </div>
                  </td>
                  <td>
                    <strong>{r.reference}</strong>
                  </td>
                  <td>
                    <StatusBadge status={r.status} map={registrationStatus} />
                  </td>
                  <td>
                    {r.status === "registered" && (
                      <ConfirmButton
                        question="Release your place?"
                        confirmLabel="Yes, cancel"
                        onConfirm={() => cancel(r)}
                      >
                        Cancel
                      </ConfirmButton>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
