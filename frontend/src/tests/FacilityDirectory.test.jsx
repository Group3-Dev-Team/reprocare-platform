import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

it('filters to facilities with public reviews from the sort menu, keeping search, county, paging and view', async () => {
  const listings = vi.spyOn(api, 'facilities').mockResolvedValue({ total: 30, items: [], page: 2, pages: 2, page_size: 15 });
  const markers = vi.spyOn(api, 'facilityMarkers').mockResolvedValue([]);
  vi.spyOn(api, 'services').mockResolvedValue([]);
  vi.spyOn(api, 'insurers').mockResolvedValue([]);
  vi.spyOn(api, 'counties').mockResolvedValue([]);
  const google = vi.spyOn(api, 'facilityGoogleReviews');
  render(
    <MemoryRouter initialEntries={['/find-care/facilities?q=hospital&county=Kisumu&view=grid']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FindCarePage />
      <CurrentUrl />
    </MemoryRouter>,
  );
  expect(screen.queryByRole('button', { name: 'Public reviews' })).toBeNull();
  const sortMenu = await screen.findByRole('combobox', { name: 'Sort by' });
  expect(within(sortMenu).getByRole('option', { name: 'Public reviews' })).toBeInTheDocument();
  expect(within(sortMenu).getAllByRole('option').map((o) => o.textContent)).toEqual(expect.arrayContaining([
    'Most relevant', 'Most complete listings', 'Name (A–Z)', 'Name (Z–A)', 'Highest Google Maps rating',
    'Most Google Maps ratings', 'Highest ReproCare patient rating', 'Most ReproCare patient reviews', 'Public reviews',
  ]));
  fireEvent.change(sortMenu, { target: { value: 'public_reviews' } });
  await waitFor(() => expect(listings).toHaveBeenLastCalledWith(
    { q: 'hospital', county: 'Kisumu', has_public_reviews: 'true', sort: 'relevance', page: 1, page_size: 15 },
    { signal: expect.any(AbortSignal) },
  ));
  expect(screen.getByRole('combobox', { name: 'Sort by' })).toHaveValue('public_reviews');
  expect(screen.getByTestId('url')).toHaveTextContent('view=grid');
  expect(screen.queryByText(/Written Google Maps reviews load on each facility page/)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Remove filter: Public reviews' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /^Map$/ }));
  await waitFor(() => expect(markers).toHaveBeenLastCalledWith(
    expect.objectContaining({ has_public_reviews: 'true', county: 'Kisumu' }), { signal: expect.any(AbortSignal) },
  ));
  fireEvent.change(screen.getByRole('combobox', { name: 'Sort by' }), { target: { value: 'google_count' } });
  await waitFor(() => expect(screen.getByTestId('url')).not.toHaveTextContent('has_public_reviews'));
  expect(screen.getByTestId('url')).toHaveTextContent('sort=google_count');
  expect(google).not.toHaveBeenCalled();
});

it('offers the towns of the chosen county and filters by county and town together', async () => {
  const listings = vi.spyOn(api, 'facilities').mockResolvedValue({ total: 3, items: [], page: 1, pages: 1, page_size: 15 });
  vi.spyOn(api, 'services').mockResolvedValue([]);
  vi.spyOn(api, 'insurers').mockResolvedValue([]);
  vi.spyOn(api, 'counties').mockResolvedValue([{ county: 'Kisumu', facility_count: 122 }, { county: 'Nakuru', facility_count: 90 }]);
  const towns = vi.spyOn(api, 'towns').mockImplementation(async (county) => (county === 'Kisumu'
    ? [{ town: 'Kisumu', county: 'Kisumu', facility_count: 98 }, { town: 'Maseno', county: 'Kisumu', facility_count: 4 }]
    : [{ town: 'Naivasha', county: 'Nakuru', facility_count: 9 }]));

  render(
    <MemoryRouter initialEntries={['/find-care/facilities']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FindCarePage />
      <CurrentUrl />
    </MemoryRouter>,
  );
  expect(screen.queryByLabelText('Town')).not.toBeInTheDocument();
  fireEvent.change(await screen.findByLabelText('County'), { target: { value: 'Kisumu' } });
  await screen.findByRole('option', { name: 'Maseno (4)' });
  expect(towns).toHaveBeenLastCalledWith('Kisumu');
  fireEvent.change(screen.getByLabelText('Town'), { target: { value: 'Maseno' } });
  await waitFor(() => expect(listings).toHaveBeenLastCalledWith(
    expect.objectContaining({ county: 'Kisumu', town: 'Maseno' }), { signal: expect.any(AbortSignal) },
  ));
  expect(screen.getByTestId('url')).toHaveTextContent('county=Kisumu&town=Maseno');
  // another county clears the town and lists that county's towns instead
  fireEvent.change(screen.getByLabelText('County'), { target: { value: 'Nakuru' } });
  await screen.findByRole('option', { name: 'Naivasha (9)' });
  expect(screen.getByTestId('url')).not.toHaveTextContent('town=');
});
