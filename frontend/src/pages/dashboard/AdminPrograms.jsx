import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import { api } from "../../services/api";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { costTypes, formatDate, programTypes } from "../../data/labels";
import { DashboardHeader } from "../../components/DashboardParts";
import { Modal } from "../../components/Modal";
import { Select, TextArea, TextInput } from "../../components/Forms";
import { Alert, ErrorState, LoadingState } from "../../components/Feedback";
import { DemoLabel } from "../../components/Badges";
import { useToast } from "../../components/Toast";

const empty = {
  title: "",
  program_type: "screening",
  summary: "",
  description: "",
  organizer_name: "",
  service_slug: "",
  venue: "",
  town: "",
  county: "",
  start_date: "",
  start_time: "9:00 am",
  end_time: "1:00 pm",
  eligibility: "",
  requirements: "",
  cost_type: "free",
  cost_note: "",
  capacity: 50,
};

export default function AdminPrograms() {
  useDocumentTitle("Community programmes");
  const toast = useToast();
  const result = useFetch(() => api.adminPrograms(), []);
  const services = useFetch(() => api.services(), []);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(empty);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [registrations, setRegistrations] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const create = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createProgram({
        ...form,
        capacity: Number(form.capacity),
        service_slug: form.service_slug || null,
      });
      toast("Programme published");
      setCreating(false);
      setForm(empty);
      result.reload();
    } catch (err) {
      setErrors(err.fields || {});
      setError(err.message);
    }
  };

  const setStatus = async (p, status) => {
    try {
      await api.updateProgram(p.slug, { status });
      toast(`Programme ${status === "cancelled" ? "cancelled" : status}`);
      result.reload();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  const showRegistrations = async (p) =>
    setRegistrations({
      program: p,
      rows: await api.programRegistrations(p.slug),
    });

  return (
    <>
      <DashboardHeader
        title="Community programmes"
        description="Publish outreach events and see who has registered."
        actions={
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            <Plus size={16} aria-hidden="true" /> New programme
          </button>
        }
      />
      {result.loading && <LoadingState rows={1} height={300} />}
      {result.error && (
        <ErrorState error={result.error} onRetry={result.reload} />
      )}
      {result.data && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Programme</th>
                <th>Date</th>
                <th>Places</th>
                <th>Status</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.data.map((p) => (
                <tr key={p.slug}>
                  <td>
                    <Link to={`/programmes/${p.slug}`}>
                      <strong>{p.title}</strong>
                    </Link>
                    <div className="small muted">
                      {p.town} · {costTypes[p.cost_type]}
                    </div>
                    {p.is_demo && <DemoLabel />}
                  </td>
                  <td>
                    {formatDate(p.start_date)}
                    {p.is_past && <div className="small muted">Past</div>}
                  </td>
                  <td>
                    {p.registered} / {p.capacity}
                  </td>
                  <td>
                    <span
                      className={`badge ${p.status === "published" ? "badge-success" : p.status === "cancelled" ? "badge-danger" : ""}`}
                    >
                      {
                        {
                          published: "Published",
                          draft: "Draft",
                          cancelled: "Cancelled",
                        }[p.status]
                      }
                    </span>
                  </td>
                  <td>
                    <div className="row" style={{ flexWrap: "nowrap" }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => showRegistrations(p)}
                      >
                        Registrations
                      </button>
                      {p.status === "published" ? (
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => setStatus(p, "cancelled")}
                        >
                          Cancel
                        </button>
                      ) : (
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setStatus(p, "published")}
                        >
                          Publish
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {creating && (
        <Modal
          title="New community programme"
          onClose={() => setCreating(false)}
          width={760}
          footer={
            <>
              <button
                className="btn btn-secondary"
                onClick={() => setCreating(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" form="program-form">
                Publish programme
              </button>
            </>
          }
        >
          <form
            id="program-form"
            className="form-grid"
            onSubmit={create}
            noValidate
          >
            {error && (
              <div className="span-2">
                <Alert tone="danger">{error}</Alert>
              </div>
            )}
            <TextInput
              className="span-2"
              label="Title"
              value={form.title}
              onChange={set("title")}
              error={errors.title}
              required
            />
            <Select
              label="Type"
              value={form.program_type}
              onChange={set("program_type")}
              options={Object.entries(programTypes).map(([value, label]) => ({
                value,
                label,
              }))}
            />
            <Select
              label="Service"
              value={form.service_slug}
              onChange={set("service_slug")}
              placeholder="None"
              options={(services.data || []).map((s) => ({
                value: s.slug,
                label: s.name,
              }))}
            />
            <TextInput
              className="span-2"
              label="One-line summary"
              value={form.summary}
              onChange={set("summary")}
              maxLength={255}
            />
            <TextArea
              className="span-2"
              label="Description"
              value={form.description}
              onChange={set("description")}
              rows={3}
            />
            <TextInput
              label="Organiser"
              value={form.organizer_name}
              onChange={set("organizer_name")}
              error={errors.organizer_name}
              required
            />
            <TextInput
              label="Venue"
              value={form.venue}
              onChange={set("venue")}
              error={errors.venue}
              required
            />
            <TextInput
              label="Town"
              value={form.town}
              onChange={set("town")}
              error={errors.town}
              required
            />
            <TextInput
              label="County"
              value={form.county}
              onChange={set("county")}
              error={errors.county}
              required
            />
            <TextInput
              label="Date"
              type="date"
              value={form.start_date}
              onChange={set("start_date")}
              error={errors.start_date}
              required
            />
            <TextInput
              label="Capacity"
              type="number"
              min={1}
              value={form.capacity}
              onChange={set("capacity")}
              error={errors.capacity}
              required
            />
            <TextInput
              label="Starts"
              value={form.start_time}
              onChange={set("start_time")}
              required
            />
            <TextInput
              label="Ends"
              value={form.end_time}
              onChange={set("end_time")}
              required
            />
            <Select
              label="Cost"
              value={form.cost_type}
              onChange={set("cost_type")}
              options={Object.entries(costTypes).map(([value, label]) => ({
                value,
                label,
              }))}
            />
            <TextInput
              label="Cost note"
              value={form.cost_note}
              onChange={set("cost_note")}
            />
            <TextArea
              className="span-2"
              label="Who can attend"
              value={form.eligibility}
              onChange={set("eligibility")}
              rows={2}
            />
            <TextArea
              className="span-2"
              label="What to bring"
              value={form.requirements}
              onChange={set("requirements")}
              rows={2}
            />
          </form>
        </Modal>
      )}

      {registrations && (
        <Modal
          title="Registrations"
          description={registrations.program.title}
          onClose={() => setRegistrations(null)}
          width={680}
        >
          {registrations.rows.length === 0 ? (
            <p className="muted">No one has registered yet.</p>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Reference</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {registrations.rows.map((r) => (
                    <tr key={r.reference}>
                      <td>{r.full_name}</td>
                      <td>{r.phone}</td>
                      <td>{r.reference}</td>
                      <td>{r.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
