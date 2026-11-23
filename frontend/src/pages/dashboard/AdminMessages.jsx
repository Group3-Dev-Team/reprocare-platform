import { useState } from "react";
import { Inbox, Mail } from "lucide-react";
import { api } from "../../services/api";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { contactTopics, formatDate } from "../../data/labels";
import { DashboardHeader, Tabs } from "../../components/DashboardParts";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/Feedback";
import { Pagination } from "../../components/Pagination";
import { useToast } from "../../components/Toast";

const labels = { new: "New", in_progress: "In progress", resolved: "Resolved" };

// messages sent from the Contact Us page (including staff access requests)
export default function AdminMessages() {
  useDocumentTitle("Contact messages");
  const [status, setStatus] = useState("new");
  const [page, setPage] = useState(1);
  const toast = useToast();
  const result = useFetch(
    () => api.adminMessages({ status, page }),
    [status, page],
  );
  const move = async (m, next) => {
    try {
      await api.updateMessage(m.reference, next);
      toast(`Marked ${labels[next].toLowerCase()}`);
      result.reload();
    } catch (e) {
      toast(e.message, "error");
    }
  };
  return (
    <>
      <DashboardHeader
        title="Contact messages"
        description="Questions, listing corrections and privacy requests sent from the Contact Us page."
      />
      <Tabs
        value={status}
        onChange={(v) => {
          setStatus(v);
          setPage(1);
        }}
        options={[
          { value: "new", label: "New" },
          { value: "in_progress", label: "In progress" },
          { value: "resolved", label: "Resolved" },
          { value: "", label: "All" },
        ]}
      />
      {result.loading && <LoadingState rows={3} height={110} />}
      {result.error && (
        <ErrorState error={result.error} onRetry={result.reload} />
      )}
      {result.data?.total === 0 && (
        <EmptyState icon={<Inbox size={24} />} title="No messages here" />
      )}
      <div className="stack">
        {(result.data?.items || []).map((m) => (
          <article key={m.reference} className="panel">
            <div className="spread">
              <div>
                <strong>{m.name}</strong>{" "}
                <span className="small muted">{m.email}</span>
                <div className="small muted">
                  {m.reference} · {formatDate(m.created_at)} ·{" "}
                  {contactTopics[m.topic]}
                </div>
              </div>
              <span
                className={`badge ${m.status === "new" ? "badge-warning" : m.status === "resolved" ? "badge-success" : "badge-info"}`}
              >
                {labels[m.status]}
              </span>
            </div>
            <p style={{ marginTop: 12, whiteSpace: "pre-wrap" }}>{m.message}</p>
            <div className="row">
              {/* opens the admin's email app with the subject filled in */}
              <a
                className="btn btn-secondary btn-sm"
                href={`mailto:${m.email}?subject=${encodeURIComponent(`Your ReproCare message ${m.reference}`)}`}
              >
                <Mail size={14} aria-hidden="true" /> Reply by email
              </a>
              {m.status !== "in_progress" && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => move(m, "in_progress")}
                >
                  Mark in progress
                </button>
              )}
              {m.status !== "resolved" && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => move(m, "resolved")}
                >
                  Mark resolved
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
      {result.data && (
        <Pagination
          page={result.data.page}
          pages={result.data.pages}
          total={result.data.total}
          pageSize={result.data.page_size}
          noun="messages"
          onChange={setPage}
        />
      )}
    </>
  );
}
