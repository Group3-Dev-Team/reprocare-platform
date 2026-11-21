/**
 * The one place the frontend talks to the backend.
 * Every page calls these functions instead of using fetch() directly.
 *
 * In the self-contained preview build (VITE_DEMO_MODE=true) requests are answered by
 * services/demoServer.js, an in-browser stand-in that uses the same demo data as the backend seed.
 */

const LOCAL_API_PROXY = import.meta.env.DEV && import.meta.env.REPROCARE_LOCAL_API_PROXY;
const API_URL = (import.meta.env.VITE_API_URL || (LOCAL_API_PROXY ? '' : 'http://localhost:8000')).replace(/\/$/, '');
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';
const TOKEN_KEY = 'reprocare.token';

export const isDemoMode = DEMO_MODE;

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: the session lasts for this page only */
  }
}

export class ApiError extends Error {
  constructor(message, status, fields = {}) {
    super(message);
    this.status = status;
    this.fields = fields; // { fieldName: message } for validation errors
  }
}

/** Turn FastAPI's error body into one readable message plus per-field messages. */
function parseError(status, body) {
  if (body && typeof body.detail === 'string') return new ApiError(body.detail, status);
  if (body && Array.isArray(body.detail)) {
    const fields = {};
    for (const item of body.detail) {
      const name = item.loc?.[item.loc.length - 1];
      if (name) fields[name] = item.msg.replace(/^Value error, /, '');
    }
    return new ApiError('Please check the highlighted fields.', status, fields);
  }
  return new ApiError('Something went wrong. Please try again.', status);
}

function toQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== false) search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

export async function request(method, path, { body, params, signal, anonymous = false } = {}) {
  const url = `/api${path}${toQuery(params)}`;
  signal?.throwIfAborted();
  const token = anonymous ? null : getToken();
  // The literal check lets Vite drop the demo server entirely from normal builds.
  if (import.meta.env.VITE_DEMO_MODE === 'true') {
    const { handleDemoRequest } = await import('./demoServer.js');
    const result = await handleDemoRequest(method, url, body, token);
    signal?.throwIfAborted();
    if (result.status >= 400) throw parseError(result.status, result.body);
    return result.body;
  }
  let response;
  try {
    response = await fetch(API_URL + url, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError('We could not reach the ReproCare server. Check your connection and try again.', 0);
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  signal?.throwIfAborted();
  if (!response.ok) {
    if (response.status === 401 && token && token === getToken()) window.dispatchEvent(new Event('reprocare:signed-out'));
    throw parseError(response.status, data);
  }
  return data;
}

const get = (path, params, options) => request('GET', path, { ...options, params });
const post = (path, body) => request('POST', path, { body });
const put = (path, body) => request('PUT', path, { body });
const patch = (path, body) => request('PATCH', path, { body });
const del = (path) => request('DELETE', path);

// These public lookup lists are shared across directory and content pages.
const referenceCache = new Map();
const REFERENCE_TTL_MS = 5 * 60 * 1000;

function reference(path) {
  const cached = referenceCache.get(path);
  if (cached && Date.now() < cached.expiresAt) return cached.result;

  const entry = { expiresAt: Infinity };
  entry.result = get(path, undefined, { anonymous: true }).then((data) => {
    entry.expiresAt = Date.now() + REFERENCE_TTL_MS;
    return data;
  }).catch((error) => {
    referenceCache.delete(path);
    throw error;
  });
  referenceCache.set(path, entry);
  return entry.result;
}

export const api = {
  // Reference data
  stats: () => get('/stats'),
  services: () => reference('/services'),
  insurers: () => reference('/insurers'),
  towns: () => reference('/towns'),
  counties: () => reference('/counties'),

  // Authentication
  authCapabilities: (options) => get('/auth/capabilities', undefined, { ...options, anonymous: true }),
  googleStart: (body) => request('POST', '/auth/google/start', { body, anonymous: true }),
  googleExchange: (body) => request('POST', '/auth/google/exchange', { body, anonymous: true }),
  googleLinkStatus: (options) => get('/auth/google/link', undefined, options),
  googleLinkStart: (body) => post('/auth/google/link/start', body),
  googleLinkExchange: (body) => post('/auth/google/link/exchange', body),
  register: (body) => request('POST', '/auth/register', { body, anonymous: true }),
  login: (body) => request('POST', '/auth/login', { body, anonymous: true }),
  logout: () => post('/auth/logout'),
  logoutAll: () => post('/auth/logout-all'),
  me: (options) => get('/auth/me', undefined, options),
  updateMe: (body) => patch('/auth/me', body),
  changePassword: (body) => post('/auth/change-password', body),
  closeAccount: (body) => post('/auth/me/close', body),

  // Discovery
  facilities: (params, options) => get('/facilities', params, options),
  facilityMarkers: (params, options) => get('/facilities/markers', params, options),
  facility: (slug, options) => get(`/facilities/${slug}`, undefined, options),
  facilityReviews: (slug, params, options) => get(`/facilities/${slug}/reviews`, params, options),
  createReview: (slug, body) => post(`/facilities/${slug}/reviews`, body),
  // External public feedback (Facebook, TikTok, Google) — separate from ReproCare reviews
  facilityPublicFeedback: (slug, options) => get(`/facilities/${slug}/public-feedback`, undefined, options),
  facilityPublicPosts: (slug, params, options) => get(`/facilities/${slug}/public-feedback/posts`, params, options),
  instagramDemoPosts: (slug, options) => get(`/local-demo/instagram/${slug}`, undefined, options),
  facebookDemoCounts: (options) => get('/local-demo/facebook/counts', undefined, options),
  facebookDemoFacilities: (options) => get('/local-demo/facebook/facilities', undefined, options),
  facebookDemoPosts: (params, options) => get('/local-demo/facebook/posts', params, options),
  facebookDemoComments: (id, params, options) => get(`/local-demo/facebook/posts/${id}/comments`, params, options),
  externalPostComments: (id, params, options) => get(`/external-posts/${id}/comments`, params, options),
  practitioners: (params, options) => get('/practitioners', params, options),
  specialties: () => reference('/practitioners/specialties'),
  practitioner: (slug) => get(`/practitioners/${slug}`),
  labTests: (params, options) => get('/lab-tests', params, options),
  reviews: (params, options) => get('/reviews', params, options),
  facilityGoogleReviews: (slug, options) => get(`/places/facilities/${slug}/reviews`, undefined, options),
  placesStatus: () => get('/places/status'),
  placesSearch: (params) => get('/places/search', params),

  // Patient account
  requestAppointment: (body) => post('/appointments', body),
  myAppointments: (params, options) => get('/me/appointments', params, options),
  cancelAppointment: (ref) => post(`/me/appointments/${ref}/cancel`),
  rescheduleAppointment: (ref, body) => post(`/me/appointments/${ref}/reschedule`, body),
  saved: () => get('/me/saved'),
  save: (slug) => put(`/me/saved/${slug}`),
  unsave: (slug) => del(`/me/saved/${slug}`),
  notifications: () => get('/me/notifications'),
  markNotificationsRead: () => post('/me/notifications/read'),
  myReviews: (options) => get('/me/reviews', undefined, options),
  myRegistrations: (options) => get('/me/registrations', undefined, options),
  cancelRegistration: (ref) => post(`/me/registrations/${ref}/cancel`),

  // Programmes and content
  programs: (params, options) => get('/programs', params, options),
  program: (slug, options) => get(`/programs/${slug}`, undefined, options),
  registerForProgram: (slug, body) => post(`/programs/${slug}/registrations`, body),
  articles: (params, options) => get('/articles', params, options),
  article: (slug, options) => get(`/articles/${slug}`, undefined, options),
  contact: (body) => post('/contact', body),

  // Facility workspace
  facilityOverview: () => get('/facility/overview'),
  facilityAppointments: (params, options) => get('/facility/appointments', params, options),
  respondToAppointment: (ref, body) => patch(`/facility/appointments/${ref}`, body),
  updateFacilityProfile: (body) => patch('/facility/profile', body),
  facilityStaffReviews: () => get('/facility/reviews'),
  replyToReview: (id, body) => put(`/facility/reviews/${id}/reply`, body),

  // Administration
  adminOverview: () => get('/admin/overview'),
  adminReviews: (params) => get('/admin/reviews', params),
  adminFacebookPosts: (params) => get('/admin/facebook-feedback', params),
  adminFacebookPost: (id) => get(`/admin/facebook-feedback/${id}`),
  moderateFacebookPost: (id, body) => post(`/admin/facebook-feedback/${id}/moderate`, body),
  moderateReview: (id, body) => post(`/admin/reviews/${id}/moderate`, body),
  adminUsers: (params) => get('/admin/users', params),
  createStaffAccount: (body) => post('/admin/users', body),
  setUserActive: (id, isActive) => patch(`/admin/users/${id}`, { is_active: isActive }),
  adminMessages: (params) => get('/admin/contact-messages', params),
  updateMessage: (ref, status) => patch(`/admin/contact-messages/${ref}`, { status }),
  adminPrograms: () => get('/admin/programs'),
  createProgram: (body) => post('/admin/programs', body),
  updateProgram: (slug, body) => patch(`/admin/programs/${slug}`, body),
  programRegistrations: (slug) => get(`/admin/programs/${slug}/registrations`),
  importHistory: () => get('/admin/imports'),
  importFacilities: (body) => post('/import/facilities', body),
};
