import { useSyncExternalStore } from 'react';

const STORAGE_KEY = 'reprocare.theme';
const SYSTEM_PREFERENCE = '(prefers-color-scheme: dark)';
let theme = 'light';
let manualTheme;
const listeners = new Set();

function readPreference() {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === 'light' || value === 'dark' ? value : undefined;
  } catch {
    return undefined;
  }
}

function systemTheme() {
  return window.matchMedia?.(SYSTEM_PREFERENCE).matches ? 'dark' : 'light';
}

function applyTheme(next) {
  const changed = theme !== next;
  theme = next;
  document.documentElement.dataset.theme = next;
  if (changed) listeners.forEach((listener) => listener());
}

export function initializeTheme() {
  manualTheme = readPreference();
  applyTheme(manualTheme ?? systemTheme());
}

function subscribe(listener) {
  const media = window.matchMedia?.(SYSTEM_PREFERENCE);
  const onSystemChange = () => {
    if (!manualTheme) applyTheme(systemTheme());
  };
  const onStorage = (event) => {
    if (event.key === STORAGE_KEY || event.key === null) initializeTheme();
  };
  if (!listeners.size) {
    media?.addEventListener('change', onSystemChange);
    window.addEventListener('storage', onStorage);
    removeListeners = () => {
      media?.removeEventListener('change', onSystemChange);
      window.removeEventListener('storage', onStorage);
    };
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (!listeners.size) removeListeners?.();
  };
}

let removeListeners;

export function useTheme() {
  return useSyncExternalStore(subscribe, () => theme);
}

export function toggleTheme() {
  manualTheme = theme === 'dark' ? 'light' : 'dark';
  try {
    window.localStorage.setItem(STORAGE_KEY, manualTheme);
  } catch {
    // The selected theme remains active in this tab without storage.
  }
  applyTheme(manualTheme);
}
