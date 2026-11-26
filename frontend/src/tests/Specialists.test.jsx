import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import SpecialistsPage from '../pages/SpecialistsPage';
import { api } from '../services/api';

const empty = { items: [], total: 0, page: 1, pages: 1, page_size: 15 };

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <SpecialistsPage />
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe('specialists directory states', () => {
  it('says profiles are not listed yet when the directory is empty', async () => {
    vi.spyOn(api, 'specialties').mockResolvedValue([]);
    vi.spyOn(api, 'towns').mockResolvedValue([]);
    vi.spyOn(api, 'practitioners').mockResolvedValue(empty);
    renderAt('/find-care/specialists?town=Nakuru');
    expect(await screen.findByText('Practitioner profiles are not listed yet')).toBeInTheDocument();
    expect(screen.queryByText('No practitioner listings match these filters')).not.toBeInTheDocument();
  });

  it('says the filters do not match when other listings exist', async () => {
    vi.spyOn(api, 'specialties').mockResolvedValue([{ name: 'Midwife', count: 3 }]);
    vi.spyOn(api, 'towns').mockResolvedValue([]);
    vi.spyOn(api, 'practitioners').mockResolvedValue(empty);
    renderAt('/find-care/specialists?specialty=Midwife&town=Lamu');
    expect(await screen.findByText('No practitioner listings match these filters')).toBeInTheDocument();
  });

  it('does not claim a filter mismatch when the specialty list failed to load', async () => {
    vi.spyOn(api, 'specialties').mockRejectedValue(new Error('offline'));
    vi.spyOn(api, 'towns').mockResolvedValue([]);
    vi.spyOn(api, 'practitioners').mockResolvedValue(empty);
    renderAt('/find-care/specialists?town=Nakuru');
    expect(await screen.findByText('No practitioner listings found for these filters')).toBeInTheDocument();
    expect(screen.queryByText('No practitioner listings match these filters')).not.toBeInTheDocument();
    expect(screen.getByText(/Some filter options could not be loaded/)).toBeInTheDocument();
  });
});
