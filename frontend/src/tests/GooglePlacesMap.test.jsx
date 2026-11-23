import { fireEvent, render, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { GooglePlacesMap } from '../components/GooglePlacesMap';

it('renders existing results after the Google Maps script finishes loading', async () => {
  const fitBounds = vi.fn();
  const markerListener = vi.fn();
  const setAnimation = vi.fn();
  const onSelect = vi.fn();
  const position = { lat: -1.2864, lng: 36.8172 };
  const Map = vi.fn(function TestMap() {
    this.fitBounds = fitBounds;
  });
  const Marker = vi.fn(function TestMarker() {
    this.getPosition = () => position;
    this.addListener = markerListener;
    this.setMap = vi.fn();
    this.setAnimation = setAnimation;
  });
  const extend = vi.fn();
  const LatLngBounds = vi.fn(function TestBounds() {
    this.extend = extend;
    this.isEmpty = () => extend.mock.calls.length === 0;
  });

  const view = render(
    <GooglePlacesMap
      places={[
        { place_id: 'coordinates-known', name: 'Test listing', latitude: position.lat, longitude: position.lng },
        { place_id: 'coordinates-missing', name: 'No map location', latitude: null, longitude: null },
      ]}
      selectedId="coordinates-known"
      onSelect={onSelect}
    />,
  );
  const script = document.head.querySelector('script[src^="https://maps.googleapis.com/maps/api/js"]');

  try {
    expect(script).not.toBeNull();
    expect(Marker).not.toHaveBeenCalled();

    vi.stubGlobal('google', { maps: { Map, Marker, LatLngBounds, Animation: { BOUNCE: 'bounce' } } });
    fireEvent.load(script);

    await waitFor(() => expect(Marker).toHaveBeenCalledExactlyOnceWith({
      position,
      map: Map.mock.instances[0],
      title: 'Test listing',
    }));
    expect(extend).toHaveBeenCalledWith(position);
    expect(fitBounds).toHaveBeenCalledWith(LatLngBounds.mock.instances[0]);
    expect(setAnimation).toHaveBeenCalledWith('bounce');
    expect(markerListener.mock.calls[0][0]).toBe('click');
    markerListener.mock.calls[0][1]();
    expect(onSelect).toHaveBeenCalledWith('coordinates-known');
  } finally {
    view.unmount();
    script?.remove();
    vi.unstubAllGlobals();
  }
});
