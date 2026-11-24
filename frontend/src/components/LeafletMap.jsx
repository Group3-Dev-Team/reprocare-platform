import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

/**
 * Interactive OpenStreetMap map (Leaflet) for ReproCare's own records.
 * Markers use real stored coordinates only. Click a marker to select it; selection is highlighted and synced with the list.
 * Pins that would overlap at the current zoom are grouped into a numbered circle; selecting it zooms in.
 * Google Places results are NOT shown here: Google's terms require them on a Google map (see GooglePlacesMap).
 *
 * props: points [{ id, name, latitude, longitude, subtitle, href, demo }], selectedId, onSelect, onPick (lat,lng), center, zoom, height
 */
const KENYA_CENTER = [0.2, 37.9];
const CLUSTER_RADIUS = 44; // pixels: pins closer than this are grouped (a pin is 26px wide, a group up to 44px)
const CLUSTER_UNTIL_ZOOM = 15; // from street level every pin is shown on its own

/** Group items {x, y} (projected pixels) lying within `radius` pixels of a group's first item. Returns arrays of items. */
export function groupNearby(items, radius = CLUSTER_RADIUS) {
  const groups = [];
  items.forEach((item) => {
    const group = groups.find(([first]) => Math.hypot(first.x - item.x, first.y - item.y) < radius);
    if (group) group.push(item);
    else groups.push([item]);
  });
  return groups;
}

function clusterIcon(count) {
  const size = count < 10 ? 32 : count < 100 ? 38 : 44;
  return L.divIcon({
    className: '',
    html: `<span class="map-cluster" style="width:${size}px;height:${size}px">${count}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

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
  const drawRef = useRef(() => {});
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
    map.current.on('zoomend', () => drawRef.current());
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

  // Draw the pins for the current zoom: overlapping pins become one numbered group, the selected pin stays visible.
  drawRef.current = () => {
    if (!map.current || !layer.current) return;
    layer.current.clearLayers();
    markers.current = {};
    const valid = points.filter((p) => p.latitude != null && p.longitude != null);
    const zoomLevel = map.current.getZoom();
    const single = (p) => {
      const marker = L.marker([p.latitude, p.longitude], { icon: markerIcon(p.id === selectedId, p.demo), title: p.name, keyboard: true, alt: p.name });
      const link = p.href ? `<a href="${escapeHtml(p.href)}" data-href="${escapeHtml(p.href)}">View details</a>` : '';
      marker.bindPopup(`<strong>${escapeHtml(p.name)}</strong><br/><span>${escapeHtml(p.subtitle || '')}</span><br/>${link}`);
      marker.on('click', () => onSelect?.(p.id));
      if (p.id === selectedId) marker.setZIndexOffset(1000);
      marker.addTo(layer.current);
      markers.current[p.id] = marker;
    };
    if (zoomLevel >= CLUSTER_UNTIL_ZOOM) {
      valid.forEach(single);
      return;
    }
    const projected = valid
      .filter((p) => p.id !== selectedId)
      .map((p) => ({ point: p, ...map.current.project([p.latitude, p.longitude], zoomLevel) }));
    groupNearby(projected).forEach((group) => {
      if (group.length === 1) {
        single(group[0].point);
        return;
      }
      const bounds = L.latLngBounds(group.map(({ point }) => [point.latitude, point.longitude]));
      const cluster = L.marker(bounds.getCenter(), {
        icon: clusterIcon(group.length),
        title: `${group.length} facilities here. Select to zoom in.`,
        alt: `${group.length} facilities`,
        keyboard: true,
        zIndexOffset: 500, // above single pins so a group is always clickable; the selected pin (1000) stays on top
      });
      cluster.on('click', () => {
        const target = map.current.getBoundsZoom(bounds.pad(0.2));
        // Pins at the same address never separate, so go straight to the zoom that shows every pin.
        map.current.setView(bounds.getCenter(), Math.min(Math.max(target, zoomLevel + 1), CLUSTER_UNTIL_ZOOM));
      });
      cluster.addTo(layer.current);
    });
    const selected = valid.find((p) => p.id === selectedId);
    if (selected) single(selected);
  };

  useEffect(() => {
    const valid = points.filter((p) => p.latitude != null && p.longitude != null);
    if (fitToPoints && valid.length) {
      // View switches can unmount the map while Leaflet's programmatic zoom is queued.
      map.current.fitBounds(L.latLngBounds(valid.map((p) => [p.latitude, p.longitude])).pad(0.15), { maxZoom: 13, animate: false });
    }
    drawRef.current();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points]);

  useEffect(() => {
    // A pin chosen from the list may be inside a group: draw again so it is shown on its own.
    if (selectedId != null && !markers.current[selectedId]) drawRef.current();
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
