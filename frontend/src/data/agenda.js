import { facilityDisplayName } from './facilityNames';

const nairobiDate = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Africa/Nairobi' });

export function nairobiToday() {
  return nairobiDate.format(new Date());
}

export async function loadAppointmentPages(fetchPage, signal) {
  const items = [];
  let page = 1;
  let result;
  do {
    signal?.throwIfAborted();
    result = await fetchPage(page, signal);
    items.push(...result.items);
    page += 1;
  } while (page <= result.pages);
  return items;
}

export function isCalendarDate(value) {
  if (typeof value !== 'string' || !/^[1-9]\d{3}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export function upcomingAgenda(appointments, registrations, today = nairobiToday()) {
  const items = new Map();
  for (const appointment of appointments) {
    const { reference, status, facility, preferred_date, preferred_time, facility_note } = appointment;
    if (!['requested', 'confirmed'].includes(status) || !isCalendarDate(preferred_date) || preferred_date < today) continue;
    const key = 'appointment-' + reference;
    items.set(key, {
      key, type: 'appointment', status, name: facilityDisplayName(facility), slug: facility.slug, date: preferred_date,
      period: preferred_time, note: facility_note, phone: facility.phone, canExport: status === 'confirmed',
    });
  }
  for (const registration of registrations) {
    const { reference, status, program } = registration;
    if (status !== 'registered' || program?.status !== 'published' || !isCalendarDate(program.start_date) || program.start_date < today) continue;
    const key = 'registration-' + reference;
    items.set(key, {
      key, type: 'programme', status, name: program.title, slug: program.slug, date: program.start_date,
      startsAt: program.start_time, endsAt: program.end_time, venue: program.venue, demo: program.is_demo, canExport: true,
    });
  }
  return [...items.values()].sort((a, b) => a.date.localeCompare(b.date) || a.name.localeCompare(b.name));
}

export function createCalendarFile(item, uid = () => globalThis.crypto.randomUUID(), generatedAt = new Date()) {
  if (!item.canExport || !isCalendarDate(item.date)) return null;
  const stamp = generatedAt.toISOString().replace(/[-:]|\.\d{3}/g, '');
  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//ReproCare//Private Calendar//EN',
    'CALSCALE:GREGORIAN',
    'BEGIN:VEVENT',
    'UID:' + uid() + '@reprocare-calendar.local',
    'DTSTAMP:' + stamp,
    'DTSTART;VALUE=DATE:' + item.date.replaceAll('-', ''),
    'SUMMARY:Private appointment',
    'STATUS:CONFIRMED',
    'CLASS:PRIVATE',
    'TRANSP:TRANSPARENT',
    'END:VEVENT',
    'END:VCALENDAR',
    '',
  ].join('\r\n');
}
