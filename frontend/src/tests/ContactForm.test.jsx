import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import ContactPage from '../pages/ContactPage';
import { AuthProvider } from '../hooks/useAuth';
import { api } from '../services/api';

afterEach(() => vi.restoreAllMocks());

function renderContact() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <ContactPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

it('gives browsers nothing to autofill in the spam trap and sends it empty', async () => {
  const send = vi.spyOn(api, 'contact').mockResolvedValue({ reference: 'MSG-1', status: 'new' });
  const { container } = renderContact();

  // Autofill fills fields that look like a website or URL; a filled trap made genuine messages fail (HTTP 400).
  expect(container.querySelector('input[id*="website" i], input[name*="website" i], input[autocomplete="url"]')).toBeNull();
  const trap = container.querySelector('.hp-field input');
  expect(trap).toHaveAttribute('autocomplete', 'off');
  expect(trap).toHaveAttribute('data-lpignore', 'true');
  expect(trap).toHaveAttribute('data-1p-ignore', 'true');
  expect(trap).toHaveAttribute('tabindex', '-1');

  fireEvent.change(screen.getByLabelText(/Your name/), { target: { value: 'Achieng Otieno' } });
  fireEvent.change(screen.getByLabelText(/Email address/), { target: { value: 'achieng@example.com' } });
  fireEvent.change(screen.getByLabelText(/^Message/), { target: { value: 'Please correct the opening hours on a listing.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
  await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
  expect(send.mock.calls[0][0]).toMatchObject({ name: 'Achieng Otieno', email: 'achieng@example.com', website: '' });
});
