import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { FacilityCard } from '../components/FacilityCard';
import { AppointmentModal } from '../components/AppointmentModal';

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

it('tells people when a facility does not take online requests and keeps a contact route', () => {
  wrap(<FacilityCard facility={facility({ accepts_appointment_requests: false, phone: '+254700000000' })} onRequest={vi.fn()} />);
  expect(screen.queryByRole('button', { name: /book appointment/i })).not.toBeInTheDocument();
  expect(screen.getByText(/online requests are not offered by this facility/i)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /contact facility/i })).toBeInTheDocument();
});

it('presents the booking as a request the facility must confirm', () => {
  wrap(<AppointmentModal facility={facility({ accepts_appointment_requests: true })} onClose={vi.fn()} />);
  expect(screen.getByRole('heading', { name: /request an appointment/i })).toBeInTheDocument();
});
