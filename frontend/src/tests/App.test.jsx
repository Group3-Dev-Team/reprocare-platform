import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { expect, it } from 'vitest';
import App from '../App';
import { AuthProvider } from '../hooks/useAuth';
import { SavedProvider } from '../hooks/useSaved';
import { CompareProvider } from '../hooks/useCompare';
import { ToastProvider } from '../components/Toast';

function renderAt(url) {
  render(
    <MemoryRouter initialEntries={[url]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider><SavedProvider><CompareProvider><ToastProvider><App /></ToastProvider></CompareProvider></SavedProvider></AuthProvider>
    </MemoryRouter>,
  );
}

it('renders the home shell', async () => {
  renderAt('/');
  expect(await screen.findByRole('heading', { level: 1, name: /Find reproductive care/ })).toBeInTheDocument();
});

it('renders the shared header and footer', async () => {
  renderAt('/');
  expect(await screen.findByRole('banner')).toBeInTheDocument();
  expect(screen.getByRole('contentinfo')).toBeInTheDocument();
});

it('shows the not-found page for unknown routes', async () => {
  renderAt('/no-such-page');
  expect(await screen.findByText('We could not find that page')).toBeInTheDocument();
});
