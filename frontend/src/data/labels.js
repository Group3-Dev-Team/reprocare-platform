/** Plain-language labels for values that come from the API. */
export const facilityTypes = [
  { value: 'hospital', label: 'Hospital' },
  { value: 'clinic', label: 'Clinic' },
  { value: 'maternity_home', label: 'Maternity home' },
  { value: 'health_centre', label: 'Health centre' },
  { value: 'laboratory', label: 'Laboratory' },
];

export const appointmentStatus = {
  requested: { label: 'Awaiting facility', tone: 'warning' },
  confirmed: { label: 'Confirmed by facility', tone: 'success' },
  declined: { label: 'Declined', tone: 'danger' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
};

export const registrationStatus = {
  registered: { label: 'Registered', tone: 'success' },
  cancelled: { label: 'Cancelled', tone: 'neutral' },
  attended: { label: 'Attended', tone: 'info' },
};

export const reviewStatus = {
  pending: { label: 'Awaiting moderation', tone: 'warning' },
  published: { label: 'Published', tone: 'success' },
  rejected: { label: 'Not published', tone: 'danger' },
};

export const programTypes = { screening: 'Screening', testing: 'Testing', education: 'Education', outreach: 'Outreach' };
export const costTypes = { free: 'Free', subsidised: 'Subsidised', paid: 'Reduced fee' };
export const timeSlots = { morning: 'Morning (8 am – 12 pm)', afternoon: 'Afternoon (12 – 4 pm)', evening: 'Evening (after 4 pm)' };
export const contactTopics = {
  general: 'General question',
  listing_correction: 'Correct a facility listing',
  privacy: 'Privacy or data request',
  technical: 'Problem using the site',
  feedback: 'Feedback or suggestion',
};

export function formatDate(iso, options = { day: 'numeric', month: 'short', year: 'numeric' }) {
  if (!iso) return '';
  const date = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return date.toLocaleDateString('en-KE', options);
}
