import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import LeafletMap, { groupNearby } from '../components/LeafletMap';
import FindCarePage from '../pages/FindCarePage';
import { api } from '../services/api';

afterEach(() => vi.restoreAllMocks());

const router = { v7_startTransition: true, v7_relativeSplatPath: true };

function CurrentUrl() {
  return <output data-testid="url">{useLocation().search}</output>;
}

describe('map pin grouping', () => {
  it('groups only pins that would overlap', () => {
    const groups = groupNearby([
      { id: 'a', x: 10, y: 10 }, { id: 'b', x: 30, y: 40 }, // 36px apart
      { id: 'c', x: 87, y: 10 }, // 77px from a: its own pin
      { id: 'd', x: 40, y: 35 }, { id: 'e', x: 46, y: 30 }, // either side of x = 44, both within 44px of a
      { id: 'f', x: 500, y: 500 },
    ]);
    expect(groups.map((g) => g.map((item) => item.id))).toEqual([['a', 'b', 'd', 'e'], ['c'], ['f']]);
  });

  const point = (id, latitude, longitude) => ({ id, name: `Facility ${id}`, latitude, longitude, href: `/facilities/${id}` });
  const sameBuilding = [point('a', -1.2864, 36.8172), point('b', -1.2864, 36.8172), point('c', -1.2864, 36.8172)];

  function renderMap(props) {
    return render(<MemoryRouter future={router}><LeafletMap fitToPoints={false} {...props} /></MemoryRouter>);
  }

  it('shows a numbered group for nearby pins at country zoom and every pin at street level', () => {
    const country = renderMap({ points: [...sameBuilding, point('far', 0.5143, 35.2698)], center: [0.2, 37.9], zoom: 6 });
    expect(country.container.querySelector('.map-cluster')).toHaveTextContent('3');
    expect(country.container.querySelectorAll('.map-pin')).toHaveLength(1); // the distant facility stays a pin
    expect(country.container.querySelector('[title="3 facilities here. Select to zoom in."]')).toBeInTheDocument();
    country.unmount();

    const street = renderMap({ points: sameBuilding, center: [-1.2864, 36.8172], zoom: 15 });
    expect(street.container.querySelector('.map-cluster')).toBeNull();
    expect(street.container.querySelectorAll('.map-pin')).toHaveLength(3);
  });

  it('never hides the selected facility inside a group', () => {
    const view = renderMap({ points: sameBuilding, selectedId: 'b', center: [0.2, 37.9], zoom: 6 });
    expect(view.container.querySelector('.map-cluster')).toHaveTextContent('2');
    expect(view.container.querySelectorAll('.map-pin.is-selected')).toHaveLength(1);
  });
});

describe('Open now filter', () => {
  it('sends open_now to the list and the map and shows it as an active filter', async () => {
    const listings = vi.spyOn(api, 'facilities').mockResolvedValue({ total: 3, items: [], page: 1, pages: 1, page_size: 15 });
    const markers = vi.spyOn(api, 'facilityMarkers').mockResolvedValue([]);
    vi.spyOn(api, 'services').mockResolvedValue([]);
    vi.spyOn(api, 'insurers').mockResolvedValue([]);
    vi.spyOn(api, 'counties').mockResolvedValue([]);
    render(
      <MemoryRouter initialEntries={['/find-care/facilities?town=Kisumu']} future={router}>
        <FindCarePage />
        <CurrentUrl />
      </MemoryRouter>,
    );

    expect(screen.getByText(/Open now uses the opening hours listed for each facility, in Kenya time/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox', { name: 'Open now' }));
    await waitFor(() => expect(listings).toHaveBeenLastCalledWith(
      { town: 'Kisumu', open_now: 'true', sort: 'relevance', page: 1, page_size: 15 }, { signal: expect.any(AbortSignal) },
    ));
    expect(screen.getByTestId('url')).toHaveTextContent('open_now=true');
    expect(screen.getAllByText('Open now').length).toBeGreaterThan(1); // the checkbox label and the active-filter chip

    fireEvent.click(screen.getByRole('button', { name: 'Map' }));
    await waitFor(() => expect(markers).toHaveBeenLastCalledWith(
      { town: 'Kisumu', open_now: 'true', sort: 'relevance' }, { signal: expect.any(AbortSignal) },
    ));
  });
});
