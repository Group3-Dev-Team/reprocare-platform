import { useEffect, useRef, useState } from 'react';

const BROWSER_KEY = import.meta.env.VITE_GOOGLE_MAPS_BROWSER_KEY;
let loader = null;

function loadGoogleMaps() {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (!loader) {
    loader = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(BROWSER_KEY)}&v=weekly`;
      script.async = true;
      script.onload = () => {
        if (window.google?.maps) resolve(window.google.maps);
        else reject(new Error('Google Maps did not initialise. Check the browser key and its allowed websites.'));
      };
      script.onerror = () => reject(new Error('Google Maps could not be loaded. Check the browser key and its allowed websites.'));
      document.head.appendChild(script);
    });
  }
  return loader;
}

export const googleMapsAvailable = Boolean(BROWSER_KEY);

/** Google Places results must be shown on a Google map (Google Maps Platform terms), so they get their own map component. */
export function GooglePlacesMap({ places, selectedId, onSelect, height = 460 }) {
  const element = useRef(null);
  const map = useRef(null);
  const markers = useRef({});
  const [error, setError] = useState(null);
  const [maps, setMaps] = useState(null);

  useEffect(() => {
    let cancelled = false;
    loadGoogleMaps()
      .then((maps) => {
        if (cancelled) return;
        map.current = new maps.Map(element.current, { center: { lat: 0.2, lng: 37.9 }, zoom: 6, mapTypeControl: false, streetViewControl: false });
        setMaps(maps);
      })
      .catch((e) => {
        loader = null;
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!maps || !map.current) return;
    Object.values(markers.current).forEach((m) => m.setMap(null));
    markers.current = {};
    const bounds = new maps.LatLngBounds();
    places.filter((p) => p.latitude != null && p.longitude != null).forEach((p) => {
      const marker = new maps.Marker({ position: { lat: p.latitude, lng: p.longitude }, map: map.current, title: p.name });
      marker.addListener('click', () => onSelect?.(p.place_id));
      markers.current[p.place_id] = marker;
      bounds.extend(marker.getPosition());
    });
    if (!bounds.isEmpty()) map.current.fitBounds(bounds);
    return () => {
      Object.values(markers.current).forEach((marker) => marker.setMap(null));
      markers.current = {};
    };
  }, [maps, places, onSelect]);

  useEffect(() => {
    if (!maps) return;
    Object.entries(markers.current).forEach(([id, m]) => m.setAnimation(id === selectedId ? maps.Animation.BOUNCE : null));
  }, [maps, places, onSelect, selectedId]);

  if (error) return <div className="alert alert-warning">{error}</div>;
  return <div ref={element} className="map" style={{ height }} role="region" aria-label="Google map of search results" />;
}
