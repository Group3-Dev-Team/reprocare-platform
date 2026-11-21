import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const initial = { data: null, loading: true, error: null };

/** Load an API result. Pass the signal to fetch to cancel obsolete requests. */
export function useFetch(load, deps = []) {
  // The dependencies describe the request inputs, so inline loaders stay stable.
  const query = useMemo(() => ({ load }), deps);
  const active = useRef(null);
  const currentQuery = useRef(null);
  const [state, setState] = useState({ ...initial, query });

  const run = useCallback(async () => {
    if (currentQuery.current !== query) return;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setState((previous) => ({ ...initial, query, data: previous.query === query ? previous.data : null }));
    try {
      const data = await query.load(controller.signal);
      if (!controller.signal.aborted) setState({ query, data, loading: false, error: null });
    } catch (error) {
      if (!controller.signal.aborted) setState({ query, data: null, loading: false, error });
    }
  }, [query]);

  useEffect(() => {
    currentQuery.current = query;
    run();
    return () => {
      currentQuery.current = null;
      active.current?.abort();
    };
  }, [query, run]);

  const { data, loading, error } = state.query === query ? state : initial;
  return { data, loading, error, reload: run };
}
