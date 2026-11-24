import { useState } from "react";
import { Database, Upload } from "lucide-react";
import { api } from "../../services/api";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { formatDate } from "../../data/labels";
import { DashboardHeader } from "../../components/DashboardParts";
import {
  Alert,
  EmptyState,
  ErrorState,
  LoadingState,
} from "../../components/Feedback";
import { useToast } from "../../components/Toast";

const example = JSON.stringify(
  {
    source: { code: "reprocare_bot", name: "ReproCare data bot" },
    is_demo: true,
    facilities: [
      {
        external_id: "example-001",
        name: "Example Test Clinic",
        facility_type: "clinic",
        town: "Nakuru",
        county: "Nakuru",
        latitude: -0.3,
        longitude: 36.07,
        services: ["contraception", "sti"],
        insurers: ["sha"],
      },
    ],
  },
  null,
  2,
);

export default function AdminImports() {
  useDocumentTitle("Data imports");
  const toast = useToast();
  const history = useFetch(() => api.importHistory(), []);
  const [payload, setPayload] = useState(example);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setError(null);
    setResult(null);
    let body;
    try {
      body = JSON.parse(payload);
    } catch {
      setError("This is not valid JSON. Check for missing commas or quotes.");
      return;
    }
    setBusy(true);
    try {
      const r = await api.importFacilities(body);
      setResult(r);
      toast(
        `Import finished: ${r.created} created, ${r.updated} updated, ${r.failed} failed`,
      );
      history.reload();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <DashboardHeader
        title="Data imports"
        description="Facility records arrive here from the independent ReproCare data bot or from an administrator. Each batch is validated, de-duplicated by source and external ID, and logged."
      />
      <div className="dash-grid two">
        <section className="panel stack">
          <h2>Run an import</h2>
          <p className="small muted">
            Paste a JSON payload that follows the ReproCare data import
            contract. Records are validated before anything is saved.
          </p>
          <label className="sr-only" htmlFor="import-json">
            Import payload (JSON)
          </label>
          <textarea
            id="import-json"
            className="textarea code"
            rows={14}
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            spellCheck={false}
          />
          {error && <Alert tone="danger">{error}</Alert>}
          {result && (
            <Alert
              tone={result.failed ? "warning" : "success"}
              title={`Batch ${result.batch_id}: ${result.created} created, ${result.updated} updated, ${result.failed} failed`}
            >
              {result.errors.map((e) => (
                <p key={e.index}>
                  Record {e.index + 1} ({e.external_id || "no ID"}): {e.error}
                </p>
              ))}
              {result.warnings.map((w) => (
                <p key={`w${w.index}`}>
                  Record {w.index + 1}: {w.warning}
                </p>
              ))}
            </Alert>
          )}
          <button className="btn btn-primary" onClick={run} disabled={busy}>
            <Upload size={16} aria-hidden="true" />{" "}
            {busy ? "Importing…" : "Import records"}
          </button>
        </section>
        <section className="panel">
          <h2>Recent batches</h2>
          {history.loading && <LoadingState rows={2} height={60} />}
          {history.error && (
            <ErrorState error={history.error} onRetry={history.reload} />
          )}
          {history.data?.length === 0 && (
            <EmptyState icon={<Database size={24} />} title="No imports yet">
              Batches from the data bot or from this form will be listed here.
            </EmptyState>
          )}
          <ul className="item-list">
            {(history.data || []).map((b) => (
              <li key={b.id}>
                <div>
                  <strong>
                    Batch {b.id} · {b.source}
                  </strong>
                  <span className="small muted">
                    {formatDate(b.created_at, {
                      day: "numeric",
                      month: "short",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
                <span className="small">
                  {b.received} received · {b.created} new · {b.updated} updated
                  · {b.failed} failed
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
