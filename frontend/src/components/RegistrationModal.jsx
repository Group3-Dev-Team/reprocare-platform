import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { formatDate } from "../data/labels";
import { Modal } from "./Modal";
import { Checkbox, TextInput } from "./Forms";
import { Alert } from "./Feedback";
import { isKenyanPhone, PHONE_MESSAGE } from "../data/phone";

// pop up for registering for a community programme, only asks for name and phone
export function RegistrationModal({ program, onClose, onDone }) {
  const { user } = useAuth();
  const location = useLocation();
  const [form, setForm] = useState({
    full_name: user?.full_name || "",
    phone: user?.phone || "",
    consent: false,
  });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(null);

  // only patients can register, others are asked to sign in
  if (!user || user.role !== "patient") {
    return (
      <Modal
        title="Register for this programme"
        description={program.title}
        onClose={onClose}
      >
        <p>
          {user
            ? "Registrations are made from a patient account."
            : "Sign in or create a free account to register and keep your reference in one place."}
        </p>
        {!user && (
          <div className="row">
            <Link
              className="btn btn-primary"
              to={`/sign-in?next=${encodeURIComponent(location.pathname)}`}
            >
              Sign in
            </Link>
            <Link
              className="btn btn-secondary"
              to={`/register?next=${encodeURIComponent(location.pathname)}`}
            >
              Create account
            </Link>
          </div>
        )}
      </Modal>
    );
  }

  const submit = async (e) => {
    e.preventDefault();
    const next = {};
    if (form.full_name.trim().length < 2)
      next.full_name = "Enter your name as it should appear on the list.";
    if (!isKenyanPhone(form.phone))
      next.phone = PHONE_MESSAGE;
    if (!form.consent)
      next.consent =
        "Please agree so the organiser can contact you about this programme.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setSending(true);
    setError(null);
    try {
      const result = await api.registerForProgram(program.slug, {
        ...form,
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
      });
      setDone(result);
      onDone?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  if (done) {
    return (
      <Modal
        title="You are registered"
        description={program.title}
        onClose={onClose}
        footer={
          <button className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        }
      >
        <div className="confirmation">
          <CheckCircle2 size={36} color="var(--green-600)" aria-hidden="true" />
          <div>
            <p>
              Your reference is <strong>{done.reference}</strong>. Show it at
              the venue on {formatDate(program.start_date)} at{" "}
              {program.start_time}.
            </p>
            <p className="small muted">
              Registration reserves a place; it is not a record of any health
              service. Find it any time under{" "}
              <Link to="/dashboard/registrations">your registrations</Link>.
            </p>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      title="Register for this programme"
      description={`${program.title} · ${formatDate(program.start_date)}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-success"
            type="submit"
            form="registration-form"
            disabled={sending}
          >
            {sending ? "Registering…" : "Register"}
          </button>
        </>
      }
    >
      <form
        id="registration-form"
        className="stack"
        onSubmit={submit}
        noValidate
      >
        {error && <Alert tone="danger">{error}</Alert>}
        <TextInput
          label="Full name"
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          error={errors.full_name}
          autoComplete="name"
          required
        />
        <TextInput
          label="Phone number"
          type="tel"
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
          error={errors.phone}
          autoComplete="tel"
          required
        />
        <Checkbox
          checked={form.consent}
          onChange={(e) => setForm({ ...form, consent: e.target.checked })}
          label="I agree that the organiser may use my name and phone number to manage this programme. ReproCare does not collect health details for registration."
        />
        {errors.consent && (
          <span className="field-error">{errors.consent}</span>
        )}
      </form>
    </Modal>
  );
}
