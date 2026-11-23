import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const CompareContext = createContext(null);
const KEY = 'reprocare.compare';
export const MAX_COMPARE = 3;

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]');
  } catch {
    return [];
  }
}

/** Up to three facilities the visitor wants to see side by side. Kept in this browser only. */
export function CompareProvider({ children }) {
  const [items, setItems] = useState(read);

  const persist = (next) => {
    setItems(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  const toggle = useCallback(
    (facility) => {
      const exists = items.some((i) => i.slug === facility.slug);
      if (exists) persist(items.filter((i) => i.slug !== facility.slug));
      else if (items.length < MAX_COMPARE) persist([...items, { slug: facility.slug, name: facility.name }]);
    },
    [items],
  );
  const clear = useCallback(() => persist([]), []);
  const value = useMemo(() => ({ items, toggle, clear, has: (slug) => items.some((i) => i.slug === slug) }), [items, toggle, clear]);
  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>;
}

export function useCompare() {
  return useContext(CompareContext);
}
