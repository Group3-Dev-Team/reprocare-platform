import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import { FacilityCard } from '../components/FacilityCard';
import { resetGooglePhotos } from '../components/GooglePhoto';

vi.mock('../hooks/useCompare', () => ({ MAX_COMPARE: 3, useCompare: () => ({ has: () => false, items: [], toggle: vi.fn() }) }));
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: null }) }));
vi.mock('../hooks/useSaved', () => ({ useSaved: () => ({ isSaved: () => false, toggle: vi.fn() }) }));
vi.mock('../components/Toast', () => ({ useToast: () => vi.fn() }));

const future = { v7_startTransition: true, v7_relativeSplatPath: true };
afterEach(() => { vi.restoreAllMocks(); resetGooglePhotos(); });

it('shows a live Google rating and photo on a linked facility card and asks only once per facility', async () => {
  const summary = vi.spyOn(api, 'facilityGoogleSummary').mockResolvedValue({ rating: 4.4, rating_count: 120, google_maps_uri: 'https://maps.google.com/?cid=9',
    photo: { photo_uri: 'https://lh3.googleusercontent.com/card', authors: [{ name: 'Fixture Photographer', url: null }] } });
  const facility = { slug: 'linked-fixture', name: 'Linked Fixture Clinic', facility_type: 'clinic', has_google_place: true, services: [], insurers: [] };
  const unlinked = { ...facility, slug: 'unlinked-fixture', name: 'Unlinked Fixture', has_google_place: false };
  const tree = (f) => <MemoryRouter future={future}><FacilityCard facility={f} /><FacilityCard facility={unlinked} /></MemoryRouter>;
  const { rerender } = render(tree(facility));
  await screen.findByText('4.4');
  expect(screen.getByText('120 Google Maps ratings')).toBeInTheDocument();
  expect(screen.getByText(/Fixture Photographer/)).toBeInTheDocument();
  rerender(tree({ ...facility }));
  expect(summary).toHaveBeenCalledTimes(1);
  expect(summary).toHaveBeenCalledWith('linked-fixture', { max_width: 480 });
});
