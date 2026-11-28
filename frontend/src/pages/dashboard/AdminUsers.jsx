import { useState } from "react";
import { UserPlus } from "lucide-react";
import { api } from "../../services/api";
import { useAuth } from "../../hooks/useAuth";
import { useFetch } from "../../hooks/useFetch";
import { useDocumentTitle } from "../../hooks/useDocumentTitle";
import { formatDate } from "../../data/labels";
import { roleLabels } from "../../data/navigation";
import { DashboardHeader, Tabs } from "../../components/DashboardParts";
import { Modal } from "../../components/Modal";
import { Select, TextInput } from "../../components/Forms";
import { Alert, ErrorState, LoadingState } from "../../components/Feedback";
import { Pagination } from "../../components/Pagination";
import { useToast } from "../../components/Toast";

export default function AdminUsers() {
  useDocumentTitle("Accounts");
  const { user: me } = useAuth();
  const toast = useToast();
  const [role, setRole] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const result = useFetch(
    () => api.adminUsers({ role, q, page }),
    [role, q, page],
  );
  // Search the full directory before applying the 40-result limit.
  const [facilityQuery, setFacilityQuery] = useState("");
  const facilities = useFetch(
    () =>
      api.facilities({
        q: facilityQuery.trim(),
        page_size: 40,
        sort: "name",
        hide_demo: false,
      }),
    [facilityQuery],
  );
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "facility_staff",
    facility_slug: "",
  });
  const [error, setError] = useState(null);
  const [errors, setErrors] = useState({});
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const create = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      // admins don't belong to a facility
      await api.createStaffAccount({
        ...form,
        facility_slug:
          form.role === "facility_staff" ? form.facility_slug : null,
      });
      toast("Account created. Share the password with the person securely.");
      setCreating(false);
      result.reload();
    } catch (err) {
      setError(err.message);
      setErrors(err.fields || {});
    }
  };

  const toggle = async (u) => {
    try {
      await api.setUserActive(u.id, !u.is_active);
      toast(u.is_active ? "Account deactivated" : "Account reactivated");
      result.reload();
    } catch (e) {
      toast(e.message, "error");
    }
  };

  return (
    <>
      <DashboardHeader
        title="Accounts"
        description="Patients register themselves. Facility staff and administrator accounts are created here."
        actions={
          <button className="btn btn-primary" onClick={() => setCreating(true)}>
            <UserPlus size={16} aria-hidden="true" /> New staff account
          </button>
        }
      />
      <div className="spread">
        <Tabs
          value={role}
          onChange={(v) => {
            setRole(v);
            setPage(1);
          }}
          options={[
            { value: "", label: "All" },
            { value: "patient", label: "Patients" },
            { value: "facility_staff", label: "Facility staff" },
            { value: "admin", label: "Administrators" },
          ]}
        />
        <input
          className="input"
          style={{ maxWidth: 280 }}
          placeholder="Search name or email"
          aria-label="Search accounts"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
      </div>
      {result.loading && <LoadingState rows={1} height={240} />}
      {result.error && (
        <ErrorState error={result.error} onRetry={result.reload} />
      )}
      {result.data && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Joined</th>
                <th>Status</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {result.data.items.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>{u.full_name}</strong>
                    <div className="small muted">{u.email}</div>
                  </td>
                  <td>
                    {roleLabels[u.role]}
                    {u.facility && (
                      <div className="small muted">{u.facility.name}</div>
                    )}
                  </td>
                  <td>{formatDate(u.created_at)}</td>
                  <td>
                    <span
                      className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}
                    >
                      {u.is_active ? "Active" : "Deactivated"}
                    </span>
                  </td>
                  {/* no button on your own row, you can't deactivate yourself */}
                  <td>
                    {u.id !== me.id && (
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => toggle(u)}
                      >
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {result.data && (
        <Pagination
          page={result.data.page}
          pages={result.data.pages}
          total={result.data.total}
          pageSize={result.data.page_size}
          noun="accounts"
          onChange={setPage}
        />
      )}
      {creating && (
        <Modal
          title="New staff account"
          onClose={() => setCreating(false)}
          footer={
            <>
              <button
                className="btn btn-secondary"
                onClick={() => setCreating(false)}
              >
                Cancel
              </button>
              <button className="btn btn-primary" form="staff-form">
                Create account
              </button>
            </>
          }
        >
          <form id="staff-form" className="stack" onSubmit={create} noValidate>
            {error && <Alert tone="danger">{error}</Alert>}
            <TextInput
              label="Full name"
              value={form.full_name}
              onChange={set("full_name")}
              error={errors.full_name}
              required
            />
            <TextInput
              label="Email"
              type="email"
              value={form.email}
              onChange={set("email")}
              error={errors.email}
              required
            />
            <TextInput
              label="Temporary password"
              type="text"
              value={form.password}
              onChange={set("password")}
              error={errors.password}
              hint="8+ characters with a number. Ask them to change it after signing in."
              required
            />
            <Select
              label="Role"
              value={form.role}
              onChange={set("role")}
              options={[
                { value: "facility_staff", label: "Facility staff" },
                { value: "admin", label: "Platform administrator" },
              ]}
            />
            {form.role === "facility_staff" && (
              <>
                <TextInput
                  label="Find facility"
                  value={facilityQuery}
                  onChange={(e) => {
                    setFacilityQuery(e.target.value);
                    setForm({ ...form, facility_slug: "" });
                  }}
                  maxLength={100}
                  hint="Type part of the facility name or town. Up to 40 matches are listed."
                />
                <Select
                  label="Facility"
                  value={form.facility_slug}
                  onChange={set("facility_slug")}
                  placeholder="Choose a facility"
                  options={(facilities.data?.items || []).map((f) => ({
                    value: f.slug,
                    label: `${f.name} (${f.town})`,
                  }))}
                  hint={
                    facilities.data?.total === 0
                      ? "No facility matches that search."
                      : undefined
                  }
                  required
                />
              </>
            )}
          </form>
        </Modal>
      )}
    </>
  );
}
