import { useEffect, useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { publicSite } from '../data/publicIndexing';
import shareImage from '../assets/reprocare-clinician-hero.webp';

const DEFAULT_TITLE = 'ReproCare — Find. Compare. Trust.';
const DEFAULT_DESCRIPTION = 'Find reproductive healthcare in Kenya. Compare facilities, explore patient and public feedback, and plan your next step.';
const PRIVATE_ROUTES = /^\/(dashboard|facebook-activity|sign-in|register|compare|prepare-for-your-visit|care-planner|forgot-password|reset-password|auth)(\/|$)/;
const PUBLIC_SITE = publicSite(import.meta.env.VITE_PUBLIC_SITE_URL);

function setHeadTag(tag, attribute, key, value) {
  const selector = `${tag}[${attribute}="${key}"]`;
  const existing = document.head.querySelector(selector);
  if (!value) {
    existing?.remove();
    return;
  }
  const node = existing ?? document.createElement(tag);
  node.setAttribute(attribute, key);
  node.setAttribute(tag === 'link' ? 'href' : 'content', value);
  if (!existing) document.head.append(node);
}

function applyMetadata({ pathname, search, title, description, type = 'website', publishedTime, modifiedTime, noIndex }) {
  const fullTitle = title ? `${title} | ReproCare` : DEFAULT_TITLE;
  const summary = description?.trim() || DEFAULT_DESCRIPTION;
  const hideFromIndex = noIndex || import.meta.env.DEV || import.meta.env.VITE_DEMO_MODE === 'true' ||
    PRIVATE_ROUTES.test(pathname) || (pathname.startsWith('/find-care') && Boolean(search));
  const isPublicHost = PUBLIC_SITE && window.location.origin === PUBLIC_SITE;
  const publicUrl = !hideFromIndex && isPublicHost ? new URL(PUBLIC_SITE) : null;
  if (publicUrl) publicUrl.pathname = pathname;
  const canonical = publicUrl?.href;

  document.title = fullTitle;
  setHeadTag('meta', 'name', 'description', summary);
  setHeadTag('meta', 'name', 'robots', hideFromIndex || !isPublicHost ? 'noindex, follow' : null);
  setHeadTag('link', 'rel', 'canonical', canonical);
  setHeadTag('meta', 'property', 'og:site_name', 'ReproCare');
  setHeadTag('meta', 'property', 'og:title', fullTitle);
  setHeadTag('meta', 'property', 'og:description', summary);
  setHeadTag('meta', 'property', 'og:type', type);
  setHeadTag('meta', 'property', 'og:url', canonical);
  setHeadTag('meta', 'property', 'og:image', canonical ? new URL(shareImage, PUBLIC_SITE).href : null);
  setHeadTag('meta', 'property', 'og:image:alt', canonical ? 'Editorial image of a healthcare worker in blue scrubs' : null);
  setHeadTag('meta', 'property', 'article:published_time', type === 'article' ? publishedTime : null);
  setHeadTag('meta', 'property', 'article:modified_time', type === 'article' ? modifiedTime : null);
}

/** Clears route metadata immediately, including while a lazy page is loading. */
export function RouteMetadata() {
  const { pathname, search } = useLocation();
  useLayoutEffect(() => applyMetadata({ pathname, search }), [pathname, search]);
  return null;
}

/** Adds the public title, description and available article dates for this page. */
export function useDocumentTitle(title, description, { type, publishedTime, modifiedTime, noIndex } = {}) {
  const { pathname, search } = useLocation();
  useEffect(() => {
    applyMetadata({ pathname, search, title, description, type, publishedTime, modifiedTime, noIndex });
  }, [pathname, search, title, description, type, publishedTime, modifiedTime, noIndex]);
}
