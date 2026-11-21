import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AppointmentCalendar } from '../components/AppointmentCalendar';
import FacilityAppointments from '../pages/dashboard/FacilityAppointments';
import { PatientAgenda } from '../components/PatientAgenda';
import { createCalendarFile, isCalendarDate, upcomingAgenda } from '../data/agenda';
import { downloadFile } from '../services/downloadFile';
import { api } from '../services/api';

vi.mock('../services/downloadFile', () => ({ downloadFile: vi.fn() }));
vi.mock('../services/api', () => ({ api: { myAppointments: vi.fn(), myRegistrations: vi.fn(), facilityAppointments: vi.fn() } }));

const appointment = (status, date, reference) => ({
  reference,
  status,
  preferred_date: date,
  preferred_time: 'morning',
  facility: { name: 'Example clinic', slug: 'example-clinic' },
  facility_note: 'Sensitive note',
});

const registration = (status, date, reference, programStatus = 'published') => ({
  reference,
  status,
  program: { title: 'Example programme', slug: 'example-programme', status: programStatus, start_date: date },
});

describe('Patient agenda', () => {
  it('keeps genuine upcoming dates in order and exports only eligible items', () => {
    const items = upcomingAgenda(
      [appointment('confirmed', '2028-01-05', 'A1'), appointment('declined', '2028-01-01', 'A2'), appointment('requested', '2028-01-03', 'A3'), appointment('confirmed', '2027-01-01', 'A4')],
      [registration('registered', '2028-01-04', 'R1'), registration('cancelled', '2028-01-02', 'R2'), registration('registered', '2028-02-30', 'R3'), registration('registered', '2028-01-05', 'R4', 'draft')],
      '2028-01-01',
    );
    expect(items.map((item) => item.date)).toEqual(['2028-01-03', '2028-01-04', '2028-01-05']);
    expect(items.map((item) => item.canExport)).toEqual([false, true, true]);
    expect(createCalendarFile(items[0])).toBeNull();
    expect(isCalendarDate('2028-02-29')).toBe(true);
    expect(isCalendarDate('2027-02-29')).toBe(false);
  });

  it('creates a date-only, one-day calendar entry with no account or facility details', () => {
    const content = createCalendarFile({
      canExport: true, date: '2028-01-05', name: 'Example clinic', note: 'Sensitive note', phone: '0700000000',
    }, () => 'calendar-id', new Date('2027-12-01T17:52:00Z'));
    expect(content).toContain('DTSTAMP:20271201T175200Z\r\nDTSTART;VALUE=DATE:20280105\r\n');
    expect(content).toContain('SUMMARY:Private appointment\r\n');
    expect(content).toContain('CLASS:PRIVATE\r\n');
    expect(content).not.toMatch(/Example clinic|Sensitive note|0700000000|LOCATION|DESCRIPTION|DTEND/);
  });

  it('loads appointment pages, merges active programme registrations and keeps pending export unavailable', async () => {
    api.myAppointments
      .mockResolvedValueOnce({ items: [appointment('requested', '2099-01-03', 'A3')], pages: 2 })
      .mockResolvedValueOnce({ items: [appointment('confirmed', '2099-01-05', 'A1')], pages: 2 });
    api.myRegistrations.mockResolvedValue([registration('registered', '2099-01-04', 'R1')]);
    render(<MemoryRouter><PatientAgenda /></MemoryRouter>);
    expect(await screen.findByText('Preferred date')).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByRole('button', { name: /export date/i })).toHaveLength(2));
    expect(api.myAppointments.mock.calls.map(([params]) => params.page)).toEqual([1, 2]);
    expect(screen.getAllByRole('listitem').map((item) => item.querySelector('time').dateTime)).toEqual(['2099-01-03', '2099-01-04', '2099-01-05']);
  });

  it('opens the month with entries, filters a day and keeps the confirmed-only export policy', async () => {
    downloadFile.mockClear();
    api.myAppointments.mockResolvedValue({ items: [
      appointment('requested', '2099-03-03', 'A3'),
      appointment('confirmed', '2099-03-06', 'A1'),
    ], pages: 1 });
    api.myRegistrations.mockResolvedValue([registration('registered', '2099-03-06', 'R1')]);
    render(<MemoryRouter><PatientAgenda /></MemoryRouter>);
    await screen.findByText('Preferred date');
    fireEvent.click(screen.getByRole('button', { name: 'Calendar' }));
    fireEvent.click(screen.getByRole('button', { name: 'Open next month with entries' }));
    expect(screen.getByRole('heading', { name: 'March 2099' })).toBeVisible();
    expect(screen.getAllByRole('button', { name: /export date/i })).toHaveLength(2);

    fireEvent.click(screen.getByRole('button', { name: /3 March 2099, 1 entry/ }));
    expect(screen.getByText('Preferred date')).toBeVisible();
    expect(screen.queryByRole('button', { name: /export date/i })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /6 March 2099, 2 entries/ }));
    expect(screen.queryByText('Preferred date')).toBeNull();
    fireEvent.click(screen.getAllByRole('button', { name: /export date/i })[0]);
    expect(downloadFile).toHaveBeenCalledWith(expect.stringContaining('DTSTART;VALUE=DATE:20990306'), expect.stringContaining('text/calendar'), 'private-appointment.ics');
    expect(downloadFile.mock.lastCall[0]).not.toMatch(/Sensitive note|Example clinic/);

    fireEvent.click(screen.getByRole('button', { name: 'Show whole month' }));
    expect(screen.getByText('Preferred date')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Next month' }));
    expect(screen.getByRole('heading', { name: 'April 2099' })).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('0 entries for April 2099');
    fireEvent.click(screen.getByRole('button', { name: 'List' }));
    expect(screen.getByText('Preferred date')).toBeVisible();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('recognizes the leap day as today in Nairobi after midnight', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    try {
      vi.setSystemTime(new Date('2028-02-28T21:30:00Z'));
      render(<AppointmentCalendar items={[{ date: '2028-02-29' }]}>{() => null}</AppointmentCalendar>);
      expect(screen.getByRole('heading', { name: 'February 2028' })).toBeVisible();
      expect(screen.getAllByRole('columnheader')).toHaveLength(7);
      expect(screen.getByRole('button', { name: /29 February 2028/ })).toHaveAttribute('aria-current', 'date');
    } finally {
      vi.useRealTimers();
    }
  });

  it('loads the provider’s confirmed visits without displaying non-confirmed appointments', async () => {
    api.facilityAppointments.mockReset();
    const visit = (reference, name, status) => ({
      ...appointment(status, '2099-04-04', reference),
      patient: { full_name: name },
      service: { name: 'Consultation' },
    });
    api.facilityAppointments
      .mockResolvedValueOnce({ items: [visit('F1', 'Calendar Patient', 'confirmed')], pages: 2 })
      .mockResolvedValueOnce({ items: [visit('F2', 'Pending Patient', 'requested')], pages: 2 });
    render(<MemoryRouter initialEntries={['/dashboard/facility/appointments?view=schedule']}><FacilityAppointments /></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button', { name: 'Open next month with entries' }));
    expect(screen.getByText('Calendar Patient')).toBeVisible();
    expect(screen.queryByText('Pending Patient')).toBeNull();
    expect(screen.getByText(/Preferred period/)).toBeVisible();
    expect(api.facilityAppointments.mock.calls.map(([params]) => params)).toEqual([
      { status: 'confirmed', page: 1, page_size: 40 },
      { status: 'confirmed', page: 2, page_size: 40 },
    ]);
  });
});
