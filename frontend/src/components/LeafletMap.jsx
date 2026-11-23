import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

/**
 * Interactive OpenStreetMap map (Leaflet) for ReproCare's own records.
 * Markers use real stored coordinates only. Click a marker to select it; selection is highlighted and synced with the list.
 * Google Places results are NOT shown here: Google's terms require them on a Google map (see GooglePlacesMap).
 *
 * props: points [{ id, name, latitude, longitude, subtitle, href, demo }], selectedId, onSelect, onPick (lat,lng), center, zoom, height
 */
const KENYA_CENTER = [0.2, 37.9];

function markerIcon(selected, demo) {
  return L.divIcon({
    className: '',
    html: `<span class="map-pin ${selected ? 'is-selected' : ''}"></span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 26],
    popupAnchor: [0, -24],
  });
}

function escapeHtml(text = '') {
  return text.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

export default function LeafletMap({ points = [], selectedId, onSelect, onPick, center, zoom = 6, height = 460, fitToPoints = true, label = 'Map of facilities' }) {
  const element = useRef(null);
  const [tilesUnavailable, setTilesUnavailable] = useState(false);
  const map = useRef(null);
  const layer = useRef(null);
  const markers = useRef({});
  const pickMarker = useRef(null);
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;

  useEffect(() => {
    const instance = L.map(element.current, { scrollWheelZoom: false }).setView(center || KENYA_CENTER, zoom);
    map.current = instance;
    let loaded = 0;
    let failed = 0;
    const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    });
    tiles.on('loading', () => { loaded = 0; failed = 0; });
    tiles.on('tileload', () => { loaded += 1; });
    tiles.on('tileerror', () => { failed += 1; });
    tiles.on('load', () => {
      if (loaded || failed) setTilesUnavailable(loaded === 0);
    });
    tiles.addTo(map.current);
    layer.current = L.layerGroup().addTo(map.current);
    map.current.on('focus', () => map.current.scrollWheelZoom.enable());
    map.current.on('blur', () => map.current.scrollWheelZoom.disable());
    // Links inside popups navigate within the app instead of reloading the page.
    map.current.on('popupopen', (e) => {
      const link = e.popup.getElement()?.querySelector('[data-href]');
      link?.addEventListener('click', (ev) => {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
        ev.preventDefault();
        navigateRef.current(link.dataset.href);
      });
    });
    return () => {
      tiles.off();
      instance.stop();
      instance.remove();
      pickMarker.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!onPick) return undefined;
    const handler = (e) => onPick(e.latlng.lat, e.latlng.lng);
    const instance = map.current;
    instance.on('click', handler);
    return () => instance.off('click', handler);
  }, [onPick]);

  useEffect(() => {
    layer.current.clearLayers();
    markers.current = {};
    const valid = points.filter((p) => p.latitude != null && p.longitude != null);
    valid.forEach((p) => {
      const marker = L.marker([p.latitude, p.longitude], { icon: markerIcon(p.id === selectedId, p.demo), title: p.name, keyboard: true, alt: p.name });
      const link = p.href ? `<a href="${escapeHtml(p.href)}" data-href="${escapeHtml(p.href)}">View details</a>` : '';
      marker.bindPopup(`<strong>${escapeHtml(p.name)}</strong><br/><span>${escapeHtml(p.subtitle || '')}</span><br/>${link}`);
      marker.on('click', () => onSelect?.(p.id));
      marker.addTo(layer.current);
      markers.current[p.id] = marker;
    });
    if (fitToPoints && valid.length) {
      // View switches can unmount the map while Leaflet's programmatic zoom is queued.
      map.current.fitBounds(L.latLngBounds(valid.map((p) => [p.latitude, p.longitude])).pad(0.15), { maxZoom: 13, animate: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points]);

  useEffect(() => {
    Object.entries(markers.current).forEach(([id, marker]) => {
      const point = points.find((p) => String(p.id) === id);
      marker.setIcon(markerIcon(id === String(selectedId), point?.demo));
      if (id === String(selectedId)) marker.setZIndexOffset(1000);
      else marker.setZIndexOffset(0);
    });
    const selected = markers.current[selectedId];
    if (selected && !map.current.getBounds().contains(selected.getLatLng())) map.current.panTo(selected.getLatLng(), { animate: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  useEffect(() => {
    if (center) {
      map.current.setView(center, zoom, { animate: false });
      if (onPick) {
        if (pickMarker.current) pickMarker.current.setLatLng(center);
        else pickMarker.current = L.circleMarker(center, { radius: 9, color: '#2563eb', weight: 3, fillOpacity: 0.25, interactive: false }).addTo(map.current);
      }
    } else if (pickMarker.current) {
      pickMarker.current.remove();
      pickMarker.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center?.[0], center?.[1], zoom]);

  return (
    <>
      <div ref={element} className="map" style={{ height }} role="region" aria-label={label} tabIndex={0} />
      {tilesUnavailable && <p className="small muted map-help" role="status">The map background could not load. You can still use available facility pins and listing details.</p>}
    </>
  );
}
