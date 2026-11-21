import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ReviewForm } from '../components/ReviewForm';
import MyAppointments from '../pages/dashboard/MyAppointments';
import { ToastProvider } from '../components/Toast';
import { api } from '../services/api';

afterEach(() => vi.restoreAllMocks());

const future = (days) => new Date(Date.now() + days * 864e5).toISOString().slice(0, 10);

describe('Review form', () => {
  it('offers the service catalogue when the listing has no recorded services', async () => {
    vi.spyOn(api, 'services').mockResolvedValue([{ slug: 'antenatal', name: 'Antenatal care' }]);
    render(<ReviewForm facility={{ slug: 'clinic', name: 'Clinic', services: [] }} onClose={() => {}} onDone={() => {}} />);
    expect(await screen.findByRole('option', { name: 'Antenatal care' })).toBeInTheDocument();
    expect(screen.getByText(/no recorded services yet/)).toBeInTheDocument();
  });

  it('uses the listing services when they exist', () => {
    const spy = vi.spyOn(api, 'services');
    render(<ReviewForm facility={{ slug: 'clinic', name: 'Clinic', services: [{ slug: 'cervical', name: 'Cervical screening' }] }} onClose={() => {}} onDone={() => {}} />);
    expect(screen.getByRole('option', { name: 'Cervical screening' })).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });
});

describe('Appointment requests page', () => {
  it('lets a patient ask for a different date on an open request', async () => {
    const request = { reference: 'APT-1', status: 'confirmed', facility: { slug: 'clinic', name: 'Clinic', phone: '' }, service: null, practitioner: null,
      preferred_date: future(5), preferred_time: 'morning', notes: '', facility_note: 'See you', created_at: '2026-11-01T08:00:00Z' };
    vi.spyOn(api, 'myAppointments').mockResolvedValue({ items: [request], total: 1, page: 1, pages: 1, page_size: 20 });
    const reschedule = vi.spyOn(api, 'rescheduleAppointment').mockResolvedValue({ ...request, status: 'requested' });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><ToastProvider><MyAppointments /></ToastProvider></MemoryRouter>);

    fireEvent.click(await screen.findByRole('button', { name: 'Request a different date' }));
    fireEvent.change(screen.getByLabelText(/New preferred date/), { target: { value: future(9) } });
    fireEvent.change(screen.getByLabelText(/Preferred time period/), { target: { value: 'evening' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send change request' }));
    await waitFor(() => expect(reschedule).toHaveBeenCalledWith('APT-1', { preferred_date: future(9), preferred_time: 'evening', notes: '' }));
  });
});
