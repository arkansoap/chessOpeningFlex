import { useCallback, useEffect, useRef, useState } from "react";
import type { JobState } from "../types";

/**
 * Follows a background job of the server (sync, analysis): polls its status
 * while it runs and calls `onFinished` once when it stops.
 */
export function useJob(fetchStatus: () => Promise<JobState>, onFinished?: (job: JobState) => void) {
  const [job, setJob] = useState<JobState | null>(null);
  const wasRunning = useRef(false);
  const onFinishedRef = useRef(onFinished);
  onFinishedRef.current = onFinished;
  const fetchRef = useRef(fetchStatus);
  fetchRef.current = fetchStatus;

  const refresh = useCallback(async () => {
    try {
      const state = await fetchRef.current();
      setJob(state);
      if (wasRunning.current && state.status !== "running") onFinishedRef.current?.(state);
      wasRunning.current = state.status === "running";
    } catch {
      // The next poll will try again.
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const running = job?.status === "running";
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => void refresh(), 1200);
    return () => clearInterval(timer);
  }, [running, refresh]);

  /** Call with the state returned when starting or stopping the job. */
  const track = useCallback((state: JobState) => {
    setJob(state);
    wasRunning.current = state.status === "running";
  }, []);

  return { job, running, refresh, track };
}
