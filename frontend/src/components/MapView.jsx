import { lazy, Suspense, useEffect, useRef, useState } from 'react';

const LeafletMap = lazy(() => import('./LeafletMap'));

export function MapView({ height = 460, defer = false, ...props }) {
  const [ready, setReady] = useState(!defer);
  const placeholder = useRef(null);

  useEffect(() => {
    if (ready) return undefined;
    if (!('IntersectionObserver' in window)) {
      setReady(true);
      return undefined;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setReady(true);
    }, { rootMargin: '200px' });
    observer.observe(placeholder.current);
    return () => observer.disconnect();
  }, [ready]);

  const fallback = <div className="map" style={{ height }} aria-label="Loading map" aria-busy="true" ref={placeholder} />;
  if (!ready) return fallback;
  return (
    <Suspense fallback={fallback}>
      <LeafletMap height={height} {...props} />
    </Suspense>
  );
}
