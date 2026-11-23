import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { useAuth } from './useAuth';

const SavedContext = createContext(null);

/** The signed-in patient's saved facility slugs, loaded once and kept in sync with the server. */
export function SavedProvider({ children }) {
  const { user } = useAuth();
  const [slugs, setSlugs] = useState(new Set());

  useEffect(() => {
    if (user?.role !== 'patient') {
      setSlugs(new Set());
      return;
    }
    api
      .saved()
      .then((rows) => setSlugs(new Set(rows.map((r) => r.slug))))
      .catch(() => {});
  }, [user]);

  const toggle = useCallback(
    async (slug) => {
      const saved = slugs.has(slug);
      await (saved ? api.unsave(slug) : api.save(slug));
      setSlugs((current) => {
        const next = new Set(current);
        if (saved) next.delete(slug);
        else next.add(slug);
        return next;
      });
      return !saved;
    },
    [slugs],
  );

  const value = useMemo(() => ({ isSaved: (slug) => slugs.has(slug), toggle }), [slugs, toggle]);
  return <SavedContext.Provider value={value}>{children}</SavedContext.Provider>;
}

export function useSaved() {
  return useContext(SavedContext);
}
