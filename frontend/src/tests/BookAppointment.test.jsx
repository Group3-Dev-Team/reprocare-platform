import { fireEvent, render, screen } from '@testing-library/react';

import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { FacilityCard } from '../components/FacilityCard';
import { AppointmentModal } from '../components/AppointmentModal';
import FindCarePage from '../pages/FindCarePage';
import { api } from '../services/api';
import { BookingContactModal } from '../components/BookingContactModal';

vi.mock('../hooks/useCompare', () => ({ MAX_COMPARE: 3, useCompare: () => ({ has: () => false, items: [], toggle: vi.fn() }) }));
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: null }) }));
vi.mock('../hooks/useSaved', () => ({ useSaved: () => ({ isSaved: () => false, toggle: vi.fn() }) }));
vi.mock('../components/Toast', () => ({ useToast: () => vi.fn() }));

const facility = (fields) => ({ slug: 'test-clinic', name: 'Test Clinic', facility_type: 'clinic', town: 'Nairobi', county: 'Nairobi', services: [], insurers: [], ...fields });
const wrap = (ui) => render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter>);

it('shows Book appointment only for facilities that take ReproCare requests', () => {
  const onRequest = vi.fn();
  wrap(<FacilityCard facility={facility({ accepts_appointment_requests: true })} onRequest={onRequest} />);
  fireEvent.click(screen.getByRole('button', { name: /book appointment/i }));
  expect(onRequest).toHaveBeenCalled();
});

it('shows Book appointment on every directory card and says before opening when online requests are not offered', () => {
  const onRequest = vi.fn();
  const card = facility({ accepts_appointment_requests: false, phone: '+254700000000' });
  wrap(<FacilityCard facility={card} onRequest={onRequest} />);
  expect(screen.getByText(/not yet taking requests through ReproCare/i)).toBeInTheDocument();
  const button = screen.getByRole('button', { name: /book appointment/i });
  expect(button).toHaveClass('btn-success');
  fireEvent.click(button);
  expect(onRequest).toHaveBeenCalledWith(card);
});

it('keeps cards without booking (saved facilities, laboratories) free of the button', () => {
  wrap(<FacilityCard facility={facility({ accepts_appointment_requests: true })} />);
  expect(screen.queryByRole('button', { name: /book appointment/i })).not.toBeInTheDocument();
});

it('presents the booking as a request the facility must confirm', () => {
  wrap(<AppointmentModal facility={facility({ accepts_appointment_requests: true })} onClose={vi.fn()} />);
  expect(screen.getByRole('heading', { name: /request an appointment/i })).toBeInTheDocument();
});

it('offers only the real contact routes when a facility does not take ReproCare requests', () => {
  wrap(<BookingContactModal facility={facility({ accepts_appointment_requests: false, phone: '+254 700 000 001', email: 'desk@example.com' })}
    website="https://example.com" directions="https://www.google.com/maps/dir/?api=1&destination=-1,36" onClose={vi.fn()} />);
  expect(screen.getByText(/does not take appointment requests through ReproCare yet/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /call \+254 700 000 001/i })).toHaveAttribute('href', 'tel:+254700000001');
  expect(screen.getByRole('link', { name: /email/i })).toHaveAttribute('href', 'mailto:desk@example.com');
  expect(screen.getByRole('link', { name: /facility website/i })).toBeInTheDocument();
  expect(screen.queryByLabelText(/preferred date/i)).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: /find participating facilities/i })).toHaveAttribute('href', '/find-care/facilities?accepts_requests=true');
});

it('says so when a non-participating facility lists no booking contact', () => {
  wrap(<BookingContactModal facility={facility({ accepts_appointment_requests: false })} onClose={vi.fn()} />);
  expect(screen.getByText(/no booking contact details are listed/i)).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: /call/i })).not.toBeInTheDocument();
});

afterEach(() => vi.restoreAllMocks());

it('opens the request form or the contact panel from a directory card, depending on participation', async () => {
  const card = (slug, name, accepts) => ({ slug, name, facility_type: 'clinic', town: 'Nairobi', county: 'Nairobi', services: [], insurers: [],
    accepts_appointment_requests: accepts, phone: '+254 700 000 002', latitude: -1.29, longitude: 36.82 });
  vi.spyOn(api, 'facilities').mockResolvedValue({ total: 2, items: [card('fixture-open', 'Fixture Taking Requests', true), card('fixture-closed', 'Fixture Phone Only', false)], page: 1, pages: 1, page_size: 15 });
  vi.spyOn(api, 'services').mockResolvedValue([]);
  vi.spyOn(api, 'insurers').mockResolvedValue([]);
  vi.spyOn(api, 'counties').mockResolvedValue([]);
  render(
    <MemoryRouter initialEntries={['/find-care/facilities']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FindCarePage />
    </MemoryRouter>,
  );
  const buttons = await screen.findAllByRole('button', { name: /book appointment/i });
  expect(buttons).toHaveLength(2);
  fireEvent.click(buttons[1]);
  expect(await screen.findByText(/does not take appointment requests through ReproCare yet/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /call \+254 700 000 002/i })).toBeInTheDocument();
  fireEvent.click(screen.getAllByRole('button', { name: 'Close' }).at(-1));
  fireEvent.click(buttons[0]);
  expect(await screen.findByRole('heading', { name: /request an appointment/i })).toBeInTheDocument();
});
