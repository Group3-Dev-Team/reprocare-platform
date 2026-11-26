import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { useFetch } from '../../hooks/useFetch';
import { useDocumentTitle } from '../../hooks/useDocumentTitle';
import { facilityDisplayName } from '../../data/facilityNames';
import { DashboardHeader } from '../../components/DashboardParts';
import { Checkbox, TextArea, TextInput } from '../../components/Forms';
import { Alert, ErrorState, LoadingState } from '../../components/Feedback';
import { LocalImagePreview } from '../../components/LocalImagePreview';
import { useToast } from '../../components/Toast';
import { FACILITY_PHONE_MESSAGE, isFacilityPhone } from '../../data/phone';

const FIELDS = ['description', 'phone', 'email', 'website', 'weekday_hours', 'saturday_hours', 'sunday_hours', 'accepts_appointment_requests', 'offers_telehealth'];

export default function FacilityProfile() {
  useDocumentTitle('Facility profile');
  const toast = useToast();
  const overview = useFetch(() => api.facilityOverview(), []);
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (overview.data) setForm(Object.fromEntries(FIELDS.map((k) => [k, overview.data.facility[k] ?? ''])));
  }, [overview.data]);

  if (overview.error) return <ErrorState error={overview.error} onRetry={overview.reload} />;
  if (!form) return <LoadingState rows={3} />;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const save = async (e) => {
    e.preventDefault();
    if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) return setErrors({ email: 'Enter a valid email address or leave it empty.' });
    if (!isFacilityPhone(form.phone)) return setErrors({ phone: FACILITY_PHONE_MESSAGE });
    setErrors({});
    setSaving(true);
    try {
      await api.updateFacilityProfile(form);
      toast('Listing updated. Changes are live on your public page.');
    } catch (err) {
      setErrors(err.fields || {});
      toast(err.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <DashboardHeader title="Facility profile" description={`What patients see on ${facilityDisplayName(overview.data.facility)}'s public listing.`} />
      <form className="panel form-grid" onSubmit={save} noValidate>
        <div className="span-2">
          <Alert tone="info">These details are shown as “Stated by the facility”. Keep them current: patients use them to decide whether to travel.</Alert>
        </div>
        <TextArea className="span-2" label="About the facility" value={form.description} onChange={set('description')} rows={4} maxLength={2000} hint="What you offer and who you serve. Avoid claims you cannot support." />
        <TextInput label="Phone" type="tel" value={form.phone} onChange={set('phone')} error={errors.phone} />
        <TextInput label="Email" type="email" value={form.email} onChange={set('email')} error={errors.email} />
        <TextInput className="span-2" label="Website" type="url" value={form.website} onChange={set('website')} />
        <TextInput label="Weekday hours" value={form.weekday_hours} onChange={set('weekday_hours')} hint="e.g. 8:00 am – 5:00 pm" />
        <TextInput label="Saturday hours" value={form.saturday_hours} onChange={set('saturday_hours')} hint="Write “Closed” if closed" />
        <TextInput label="Sunday hours" value={form.sunday_hours} onChange={set('sunday_hours')} hint="Write “Closed” if closed" />
        <div className="stack span-2">
          <Checkbox checked={form.accepts_appointment_requests} onChange={set('accepts_appointment_requests')} label="Accept appointment requests through ReproCare" />
          <Checkbox checked={form.offers_telehealth} onChange={set('offers_telehealth')} label="We offer telehealth consultations" />
        </div>
        <div className="span-2">
          <button className="btn btn-primary btn-lg" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button>
        </div>
      </form>
      <LocalImagePreview />
    </>
  );
}
