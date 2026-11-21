import { useEffect, useState } from 'react';
import { Star } from 'lucide-react';
import { api } from '../services/api';
import { Checkbox, Select, TextArea, TextInput } from './Forms';
import { Alert } from './Feedback';
import { Modal } from './Modal';

/** Share an experience. Reviews are moderated before publication and never become a clinical rating. */
export function ReviewForm({ facility, onClose, onDone }) {
  const [form, setForm] = useState({ rating: 0, title: '', body: '', service_slug: '', visit_month: '', consent: false });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState(null);
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  // When the listing has no recorded services yet, the patient can still name the service they received
  // from the general catalogue. That records their visit; it does not add the service to the listing.
  const listed = facility.services || [];
  const [catalogue, setCatalogue] = useState([]);
  useEffect(() => {
    if (listed.length) return undefined;
    let active = true;
    api.services().then((items) => active && setCatalogue(items || [])).catch(() => active && setCatalogue([]));
    return () => { active = false; };
  }, [listed.length]);
  const serviceOptions = (listed.length ? listed : catalogue).map((s) => ({ value: s.slug, label: s.name }));

  const submit = async (e) => {
    e.preventDefault();
    const next = {};
    if (!form.rating) next.rating = 'Choose a rating from 1 to 5.';
    if (form.title.trim().length < 4) next.title = 'Add a short title (at least 4 characters).';
    if (form.body.trim().length < 20) next.body = 'Describe your experience in at least 20 characters.';
    if (!form.consent) next.consent = 'Please confirm before sending.';
    setErrors(next);
    if (Object.keys(next).length) return;
    setSending(true);
    setError(null);
    try {
      await api.createReview(facility.slug, {
        rating: form.rating,
        title: form.title.trim(),
        body: form.body.trim(),
        service_slug: form.service_slug || null,
        visit_month: form.visit_month ? `${form.visit_month}-01` : null,
        consent: true,
      });
      setDone(true);
      onDone?.();
    } catch (err) {
      setError(err.message);
      setErrors(err.fields || {});
    } finally {
      setSending(false);
    }
  };

  if (done) {
    return (
      <Modal title="Thank you for sharing" onClose={onClose} footer={<button className="btn btn-primary" onClick={onClose}>Done</button>}>
        <p>Your experience is with our moderators. We check that it follows the community guidelines and contains no personal health details before it is published.</p>
        <p className="small muted">You can follow its status under My reviews.</p>
      </Modal>
    );
  }

  return (
    <Modal
      title="Share your experience"
      description={facility.name}
      onClose={onClose}
      footer={
        <>
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" type="submit" form="review-form" disabled={sending}>
            {sending ? 'Sending…' : 'Send for moderation'}
          </button>
        </>
      }
    >
      <form id="review-form" className="stack" onSubmit={submit} noValidate>
        {error && <Alert tone="danger">{error}</Alert>}
        <fieldset className="rating-input">
          <legend className="field-label">Overall experience</legend>
          <div className="row">
            {[1, 2, 3, 4, 5].map((n) => (
              <label key={n} className={`star-choice ${n <= form.rating ? 'on' : ''}`}>
                <input type="radio" name="rating" value={n} checked={form.rating === n} onChange={() => setForm({ ...form, rating: n })} />
                <Star size={26} fill="currentColor" strokeWidth={0} aria-hidden="true" />
                <span className="sr-only">{n} out of 5</span>
              </label>
            ))}
          </div>
          {errors.rating && <span className="field-error">{errors.rating}</span>}
        </fieldset>
        <div className="form-grid">
          <Select
            label="Service used"
            value={form.service_slug}
            onChange={set('service_slug')}
            placeholder="General visit or not sure"
            hint={listed.length ? undefined : 'This listing has no recorded services yet. Choose the service you received, if any.'}
            options={serviceOptions}
          />
          <TextInput label="Month of visit" type="month" value={form.visit_month} onChange={set('visit_month')} max={new Date().toISOString().slice(0, 7)} />
        </div>
        <TextInput label="Title" value={form.title} onChange={set('title')} error={errors.title} maxLength={160} required />
        <TextArea label="Your experience" value={form.body} onChange={set('body')} error={errors.body} maxLength={3000} hint="Waiting time, communication, privacy, cost clarity. Please leave out names and medical details." required />
        <Checkbox checked={form.consent} onChange={(e) => setForm({ ...form, consent: e.target.checked })} label="This is my own experience, and ReproCare may publish it with my first name and initial after moderation." />
        {errors.consent && <span className="field-error">{errors.consent}</span>}
      </form>
    </Modal>
  );
}
