import { useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import '../styles/google-photo.css';

// One lookup per place per page session. Google photo URLs are short-lived, so nothing is kept beyond that.
const lookups = new Map();
let unavailable = false; // set after the server reports photos are off or capped, to stop further requests

function lookup(key, load) {
  if (!lookups.has(key)) {
    lookups.set(key, load().catch((error) => {
      if ([429, 503].includes(error?.status)) unavailable = true;
      return null;
    }));
  }
  return lookups.get(key);
}

export function resetGooglePhotos() {
  lookups.clear();
  unavailable = false;
}

/**
 * A Google Maps photo of the place with its photographer attribution, fetched only when it scrolls into view.
 * Shows `fallback` until a genuine photo is available, and keeps it when there is none.
 */
export function GooglePhoto({ slug, placeId, width = 480, alt = '', fallback }) {
  const box = useRef(null);
  const [photo, setPhoto] = useState(null);
  const key = slug ? `facility:${slug}` : placeId ? `place:${placeId}` : null;

  useEffect(() => {
    if (!key || unavailable) return undefined;
    let active = true;
    const load = () => lookup(key, () => (slug ? api.facilityGooglePhoto(slug, { max_width: width }) : api.livePlacePhoto(placeId, { max_width: width })))
      .then((found) => { if (active && found?.photo_uri) setPhoto(found); });
    if (typeof IntersectionObserver === 'undefined' || !box.current) {
      load();
      return () => { active = false; };
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        observer.disconnect();
        load();
      }
    }, { rootMargin: '200px' });
    observer.observe(box.current);
    return () => { active = false; observer.disconnect(); };
  }, [key, slug, placeId, width]);

  if (!photo) return <span ref={box} className="google-photo-slot">{fallback}</span>;
  const authors = photo.authors || [];
  return (
    <figure className="google-photo">
      <img src={photo.photo_uri} alt={alt} loading="lazy" referrerPolicy="no-referrer" />
      <figcaption>
        {authors.length > 0 && <>Photo: {authors.map((a, i) => (
          <span key={a.name}>{i > 0 && ', '}{a.url ? <a href={a.url} target="_blank" rel="noreferrer">{a.name}</a> : a.name}</span>
        ))} · </>}Google Maps
      </figcaption>
    </figure>
  );
}
