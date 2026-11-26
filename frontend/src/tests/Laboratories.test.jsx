import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import LaboratoriesPage from '../pages/LaboratoriesPage';

afterEach(() => vi.restoreAllMocks());

function CurrentUrl() {
  return <output data-testid="url">{useLocation().search}</output>;
}

it('filters laboratories county first, then by a town of that county, and resets the town with the county', async () => {
  vi.spyOn(api, 'counties').mockResolvedValue([
    { county: 'Kisumu', facility_count: 3, contextual: true }, { county: 'Nakuru', facility_count: 1, contextual: true },
  ]);
  const towns = vi.spyOn(api, 'towns').mockImplementation(async (county) => (county === 'Kisumu'
    ? [{ town: 'Kisumu', facility_count: 2 }, { town: 'Maseno', facility_count: 1 }]
    : [{ town: 'Naivasha', facility_count: 1 }]));
  const labs = vi.spyOn(api, 'facilities').mockResolvedValue({ total: 0, items: [], page: 1, pages: 0, page_size: 15 });
  const tests = vi.spyOn(api, 'labTests').mockResolvedValue({ total: 0, items: [], page: 1, pages: 0, page_size: 15 });
  render(
    <MemoryRouter initialEntries={['/find-care/laboratories']}>
      <LaboratoriesPage />
      <CurrentUrl />
    </MemoryRouter>,
  );
  expect(screen.getByLabelText('Town')).toBeDisabled();
  fireEvent.change(await screen.findByLabelText('County'), { target: { value: 'Kisumu' } });
  expect(await screen.findByRole('option', { name: 'Maseno (1 laboratory)' })).toBeInTheDocument();
  expect(towns).toHaveBeenLastCalledWith('Kisumu', { facility_type: 'laboratory' });
  fireEvent.change(screen.getByLabelText('Town'), { target: { value: 'Maseno' } });
  await waitFor(() => expect(labs).toHaveBeenLastCalledWith(
    { facility_type: 'laboratory', county: 'Kisumu', town: 'Maseno', page: 1, page_size: 15 }, { signal: expect.any(AbortSignal) },
  ));
  expect(tests).toHaveBeenLastCalledWith(expect.objectContaining({ county: 'Kisumu', town: 'Maseno' }), { signal: expect.any(AbortSignal) });
  fireEvent.change(screen.getByLabelText('County'), { target: { value: 'Nakuru' } });
  await waitFor(() => expect(screen.getByTestId('url')).toHaveTextContent('?county=Nakuru'));
  expect(screen.getByTestId('url')).not.toHaveTextContent('town=');
  expect(await screen.findByText('No laboratories listed in Nakuru')).toBeInTheDocument();
});
