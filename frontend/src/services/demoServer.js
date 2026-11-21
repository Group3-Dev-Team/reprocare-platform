/**
 * In-browser stand-in for the API, used only by the single-file preview build (VITE_DEMO_MODE=true).
 * Feature workstreams register fixture-backed handlers here with the same paths and shapes as the real API.
 */
const handlers = [
  { method: 'GET', path: '/api/health', respond: () => ({ status: 200, body: { status: 'ok' } }) },
];

export async function handleDemoRequest(method, url) {
  const path = url.split('?')[0];
  const handler = handlers.find((h) => h.method === method && h.path === path);
  if (handler) return handler.respond();
  return { status: 503, body: { detail: 'This feature is not available in the offline preview.' } };
}
