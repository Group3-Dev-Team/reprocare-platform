import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { LiveGoogleResults } from '../components/LiveGoogleResults';

const future = { v7_startTransition: true, v7_relativeSplatPath: true };
afterEach(() => vi.restoreAllMocks());

it('searches Google Maps from Find Care only when asked, and marks places not yet in the directory', async () => {
  const search = vi.spyOn(api, 'placesSearch').mockResolvedValue({ attribution: 'Results from Google Maps', next_page_token: null, results: [
    { place_id: 'ChIJfixtureListed', name: 'Fixture Listed Clinic', rating: 4.1, rating_count: 20, facility_slug: 'fixture-listed' },
    { place_id: 'ChIJfixtureExtra1', name: 'Fixture Extra Clinic', rating: 4.6, rating_count: 9, facility_slug: null },
  ] });
  render(<MemoryRouter future={future}><LiveGoogleResults query="maternity in Nakuru" /></MemoryRouter>);
  expect(search).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Search Google Maps for “maternity in Nakuru”' }));
  await screen.findByText('Fixture Extra Clinic');
  expect(search).toHaveBeenCalledWith(expect.objectContaining({ q: 'maternity in Nakuru', max_results: 20 }));
  expect(screen.getByText(/2 places, 1 not in the ReproCare directory/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'View details and reviews' })).toHaveAttribute('href', '/find-care/google/place/ChIJfixtureExtra1');
});
