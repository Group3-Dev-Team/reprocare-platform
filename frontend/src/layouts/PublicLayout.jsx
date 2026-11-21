import { Suspense, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { LoadingState } from '../components/Feedback';

/** Public page frame: skip link, header, routed page and footer. Feature-specific overlays are added by their workstreams. */
export function PublicLayout() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) window.scrollTo(0, 0);
  }, [pathname, hash]);
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Header />
      <main id="main" tabIndex={-1}>
        <Suspense fallback={<div className="container section"><LoadingState rows={2} /></div>}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
