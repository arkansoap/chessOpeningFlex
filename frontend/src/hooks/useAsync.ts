import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../services/api";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Fetch again, keeping the current data on screen meanwhile. */
  reload: () => void;
  /** Replace the data locally after a mutation. */
  setData: (data: T | null) => void;
}

/**
 * Loads data when `deps` change. A response that arrives after a newer request
 * has started is dropped, so fast navigation never shows a stale position.
 */
export function useAsync<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[]
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    fetcherRef
      .current(controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(errorMessage(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload, setData };
}
