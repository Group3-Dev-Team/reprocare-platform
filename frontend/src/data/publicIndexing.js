export const publicNavigationPaths = [
  '/', '/find-care/facilities', '/find-care/specialists', '/find-care/laboratories',
  '/find-care/insurance', '/compare', '/prepare-for-your-visit', '/health-community/programmes', '/health-community/free-care', '/health-community/alerts',
  '/health-library', '/assistant', '/patient-experiences', '/about', '/how-it-works',
  '/trust', '/contact', '/privacy', '/terms',
];

export function publicSite(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password &&
      url.pathname === '/' && !url.search && !url.hash ? url.origin : null;
  } catch {
    return null;
  }
}

export function indexingFiles(origin) {
  const robots = origin
    ? `User-agent: *\nDisallow: /api/\nDisallow: /dashboard\nDisallow: /facebook-activity\nDisallow: /auth/\nDisallow: /reset-password\nSitemap: ${origin}/sitemap.xml\n`
    : 'User-agent: *\nDisallow: /\n';
  const routes = origin ? publicNavigationPaths : [];
  const sitemap = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...routes.map((path) => `  <url><loc>${new URL(path, origin).href.replaceAll("&", "&amp;")}</loc></url>`),
    '</urlset>',
    '',
  ].join('\n');
  return { robots, sitemap };
}
