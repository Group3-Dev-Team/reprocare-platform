import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import ContactPage from '../pages/ContactPage';
import { StaffAccessEnquiry } from '../components/StaffAccessEnquiry';
import { AuthProvider } from '../hooks/useAuth';
import { api } from '../services/api';

afterEach(() => vi.restoreAllMocks());

it('explains that staff access is verified and carries facility and role to the contact form as the last step', async () => {
  vi.spyOn(api, 'facilities').mockResolvedValue({ total: 0, items: [], page: 1, pages: 0 });
  render(
    <MemoryRouter initialEntries={['/register']}>
      <AuthProvider>
        <Routes>
          <Route path="/register" element={<StaffAccessEnquiry />} />
          <Route path="/contact" element={<ContactPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
  expect(screen.getByText(/not self-registered/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText(/Facility or clinic/), { target: { value: 'Kisumu County Hospital' } });
  fireEvent.change(screen.getByLabelText(/Role/), { target: { value: 'Nurse' } });
  fireEvent.click(screen.getByRole('button', { name: 'Continue: add your contact details' }));
  expect(await screen.findByText('Staff access enquiry: last step')).toBeInTheDocument();
  expect(screen.getByLabelText(/Message/)).toHaveValue('Staff access enquiry\nFacility: Kisumu County Hospital\nRole: Nurse\n');
  expect(screen.getByLabelText(/What is it about/)).toHaveValue('general');
});
