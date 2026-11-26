import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import GooglePlacesPage from '../pages/GooglePlacesPage';
import LivePlacePage from '../pages/LivePlacePage';
import { GooglePhoto, resetGooglePhotos } from '../components/GooglePhoto';

afterEach(() => { vi.restoreAllMocks(); resetGooglePhotos(); });

it('runs a search passed from Find Care and separates listed places from live Google results', async () => {
  vi.spyOn(api, 'placesStatus').mockResolvedValue({ configured: true });
  const search = vi.spyOn(api, 'placesSearch').mockResolvedValue({ attribution: 'Results from Google Maps', next_page_token: null, results: [
    { place_id: 'ChIJfixtureListed', name: 'Fixture Listed Clinic', rating: 4.2, rating_count: 31, facility_slug: 'fixture-listed' },
    { place_id: 'ChIJfixtureLive01', name: 'Fixture Live Clinic', rating: null, rating_count: null, facility_slug: null },
  ] });
  render(<MemoryRouter initialEntries={['/find-care/google?q=Marie%20Stopes']}><GooglePlacesPage /></MemoryRouter>);
  await screen.findByText('Fixture Live Clinic');
  expect(search).toHaveBeenCalledTimes(1);
  expect(search).toHaveBeenCalledWith(expect.objectContaining({ q: 'Marie Stopes' }));
  expect(screen.getByText(/4\.2/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Open ReproCare listing' })).toHaveAttribute('href', '/facilities/fixture-listed');
  expect(screen.getByRole('link', { name: 'View details and reviews' })).toHaveAttribute('href', '/find-care/google/place/ChIJfixtureLive01');
  expect(screen.getByText('Live Google Maps result')).toBeInTheDocument();
});

it('shows a live listing as unstored, with its rating, and loads written reviews only when asked', async () => {
  vi.spyOn(api, 'livePlace').mockResolvedValue({ place_id: 'ChIJfixtureLive01', name: 'Fixture Live Clinic', address: 'Fixture Road', rating: 3.8,
    rating_count: 12, google_maps_uri: 'https://maps.google.com/?cid=1', phone: '', website: '', attribution: 'Details from Google Maps', facility_slug: null });
  vi.spyOn(api, 'livePlacePhoto').mockRejectedValue(Object.assign(new Error('off'), { status: 429 }));
  const reviews = vi.spyOn(api, 'livePlaceReviews').mockResolvedValue({ returned_count: 1, attributions: [], reviews: [
    { text: 'Fixture review text', rating: 4, source: 'https://maps.google.com/r/1', author: 'Fixture Author' },
  ] });
  render(<MemoryRouter initialEntries={['/find-care/google/place/ChIJfixtureLive01']}>
    <Routes><Route path="/find-care/google/place/:placeId" element={<LivePlacePage />} /></Routes>
  </MemoryRouter>);
  await screen.findByText('Live Google Maps result');
  expect(screen.getByText('3.8')).toBeInTheDocument();
  expect(reviews).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Load written Google Maps reviews' }));
  await screen.findByText('Fixture review text');
  expect(screen.getByText('Fixture Author')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'View this review on Google Maps' })).toHaveAttribute('href', 'https://maps.google.com/r/1');
});

it('keeps the icon when photos are unavailable and stops asking after the server says so', async () => {
  const photo = vi.spyOn(api, 'facilityGooglePhoto').mockRejectedValue(Object.assign(new Error('off'), { status: 429 }));
  const { rerender } = render(<GooglePhoto slug="a" fallback={<span>icon-a</span>} />);
  await waitFor(() => expect(photo).toHaveBeenCalledTimes(1));
  expect(screen.getByText('icon-a')).toBeInTheDocument();
  rerender(<GooglePhoto slug="b" fallback={<span>icon-b</span>} />);
  expect(screen.getByText('icon-b')).toBeInTheDocument();
  expect(photo).toHaveBeenCalledTimes(1);
});

it('shows a genuine photo with the photographer credit', async () => {
  vi.spyOn(api, 'facilityGooglePhoto').mockResolvedValue({ photo_uri: 'https://lh3.googleusercontent.com/fixture', authors: [{ name: 'Fixture Photographer', url: 'https://maps.google.com/contrib/1' }] });
  render(<GooglePhoto slug="c" alt="Google Maps photo of Fixture" fallback={<span>icon</span>} />);
  const img = await screen.findByRole('img', { name: 'Google Maps photo of Fixture' });
  expect(img).toHaveAttribute('src', 'https://lh3.googleusercontent.com/fixture');
  expect(screen.getByRole('link', { name: 'Fixture Photographer' })).toBeInTheDocument();
  expect(screen.getByText(/Google Maps/)).toBeInTheDocument();
});
