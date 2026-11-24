import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { facilityDisplayName } from '../data/facilityNames';
import { api } from '../services/api';
import FindCarePage from '../pages/FindCarePage';

afterEach(() => vi.restoreAllMocks());

function CurrentUrl() {
  return <output data-testid="url">{useLocation().search}</output>;
}

it('keeps explicit sorting and precise browser location private while applying a radius', async () => {
  const search = vi.spyOn(api, 'facilities').mockResolvedValue({ total: 630, items: [], page: 1, pages: 1 });
  vi.spyOn(api, 'services').mockResolvedValue([]);
  vi.spyOn(api, 'insurers').mockResolvedValue([]);
  vi.spyOn(api, 'counties').mockResolvedValue([]);
  const original = Object.getOwnPropertyDescriptor(navigator, 'geolocation');
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
    getCurrentPosition: (success) => success({ coords: { latitude: -1.2921, longitude: 36.8219 } }),
  } });

  try {
    render(
      <MemoryRouter initialEntries={['/find-care/facilities?sort=name']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <FindCarePage />
        <CurrentUrl />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Use my location' }));
    fireEvent.change(await screen.findByLabelText('Distance limit'), { target: { value: '10' } });
    await waitFor(() => expect(search).toHaveBeenLastCalledWith(
      { lat: -1.2921, lng: 36.8219, sort: 'name', radius_km: '10', page: 1, page_size: 15 },
      { signal: expect.any(AbortSignal) },
    ));
    expect(screen.getByTestId('url')).toHaveTextContent('?sort=name');
    expect(screen.queryByText(/nearest first/i)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Sort by'), { target: { value: 'distance' } });
    expect(await screen.findByText(/nearest first/i)).toBeInTheDocument();
    expect(screen.getByTestId('url')).toHaveTextContent('?sort=distance');
  } finally {
    if (original) Object.defineProperty(navigator, 'geolocation', original);
    else delete navigator.geolocation;
  }
});

it('uses reviewed capitalization while preserving acronyms, established case and unknown names', () => {
  expect(facilityDisplayName({ name: 'AFA IVF CONSULTANTS.' })).toBe('AFA IVF Consultants.');
  expect(facilityDisplayName({ name: 'pema maternity hospital' })).toBe('Pema Maternity Hospital');
  expect(facilityDisplayName({ name: 'AAR Healthcare' })).toBe('AAR Healthcare');
  expect(facilityDisplayName({ name: 'MIXED ABBREVIATIONS INC' })).toBe('MIXED ABBREVIATIONS INC');
});


it('preserves filters and paging across grid, map and list views', async () => {
  const listings = vi.spyOn(api, 'facilities').mockResolvedValue({ total: 30, items: [], page: 2, pages: 2, page_size: 15 });
  const markers = vi.spyOn(api, 'facilityMarkers').mockResolvedValue([]);
  vi.spyOn(api, 'services').mockResolvedValue([]);
  vi.spyOn(api, 'insurers').mockResolvedValue([]);
  vi.spyOn(api, 'counties').mockResolvedValue([{ county: 'Nairobi', facility_count: 30 }]);
  render(
    <MemoryRouter initialEntries={['/find-care/facilities?county=Nairobi&page=2&min_google_rating=4&sort=google_count']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FindCarePage />
      <CurrentUrl />
    </MemoryRouter>,
  );

  fireEvent.click(screen.getByRole('button', { name: 'Grid' }));
  expect(screen.getByRole('button', { name: 'Grid' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByTestId('url')).toHaveTextContent('page=2&min_google_rating=4&sort=google_count&view=grid');
  fireEvent.click(screen.getByRole('button', { name: 'Map' }));
  await waitFor(() => expect(markers).toHaveBeenCalledWith(
    { county: 'Nairobi', min_google_rating: '4', sort: 'google_count' }, { signal: expect.any(AbortSignal) },
  ));
  expect(listings).toHaveBeenCalledWith(
    { county: 'Nairobi', min_google_rating: '4', sort: 'google_count', page: 2, page_size: 15 }, { signal: expect.any(AbortSignal) },
  );
  fireEvent.click(screen.getByRole('button', { name: 'List' }));
  expect(screen.getByTestId('url')).toHaveTextContent('page=2&min_google_rating=4&sort=google_count&view=list');
});
