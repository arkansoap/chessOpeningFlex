import { useEffect, useRef, useState } from "react";
import { getEngine } from "../engine/stockfish";
import type { EngineAnalysis, EngineLine, EngineStatus } from "../engine/types";

export interface UseChessEngineOptions {
  /** Position to analyze. Pass `null` to leave the engine idle. */
  fen: string | null;
  /** Set to false to keep the engine stopped (user toggle). */
  enabled?: boolean;
  /** How many principal variations to report. */
  multiPv?: number;
  /** Search stops once this depth is reached. */
  maxDepth?: number;
  /**
   * Delay before starting a search after `fen` changes, so that stepping
   * quickly through a variant does not restart the engine on every keypress.
   */
  debounceMs?: number;
}

export interface UseChessEngineResult {
  lines: EngineLine[];
  depth: number;
  nps: number | null;
  /** True while the engine is still deepening the current position. */
  running: boolean;
  status: EngineStatus;
  /** Human-readable reason why the engine is unavailable, if it is. */
  error: string | null;
  /** True when the multi-threaded WASM build is in use. */
  threaded: boolean;
}

const EMPTY: EngineLine[] = [];

/**
 * Runs Stockfish on a position and exposes its top lines, refreshed live as
 * the search deepens. The engine restarts whenever `fen` changes and stops
 * when the hook unmounts or `enabled` goes false.
 */
export function useChessEngine({
  fen,
  enabled = true,
  multiPv = 5,
  maxDepth = 20,
  debounceMs = 150,
}: UseChessEngineOptions): UseChessEngineResult {
  const [analysis, setAnalysis] = useState<EngineAnalysis | null>(null);
  const [status, setStatus] = useState<EngineStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  // Tracks the position the latest results belong to, so that callbacks from a
  // search we already replaced are discarded instead of flashing on screen.
  const wantedFen = useRef<string | null>(null);
  const engine = getEngine();

  useEffect(() => {
    wantedFen.current = enabled ? fen : null;

    if (!enabled) {
      // Tear the worker down rather than just halting the search: stopping
      // frees the CPU but leaves the ~7 MB of compiled WASM, the hash table
      // and the engine threads resident. Turning the analysis off is meant to
      // give those back. Re-enabling costs a WASM recompile of about a second.
      engine.destroy();
      setAnalysis(null);
      setStatus((prev) => (prev === "unavailable" ? prev : "idle"));
      return;
    }

    if (!fen) {
      engine.stop();
      setAnalysis(null);
      setStatus((prev) => (prev === "unavailable" ? prev : "idle"));
      return;
    }

    let cancelled = false;
    setAnalysis(null);

    const timer = setTimeout(() => {
      setStatus((prev) => (prev === "ready" ? "analyzing" : "loading"));
      engine
        .init()
        .then(() => {
          if (cancelled || wantedFen.current !== fen) return;
          setError(null);
          setStatus("analyzing");
          engine.analyse(fen, { multiPv, maxDepth }, (result) => {
            if (cancelled || wantedFen.current !== result.fen) return;
            setAnalysis(result);
            if (result.finished) setStatus("ready");
          });
        })
        .catch((err: unknown) => {
          if (cancelled) return;
          setStatus("unavailable");
          setError(err instanceof Error ? err.message : String(err));
        });
    }, debounceMs);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [engine, fen, enabled, multiPv, maxDepth, debounceMs]);

  // Release the worker when the panel goes away, so navigating to another page
  // does not leave an idle engine holding memory and threads.
  useEffect(() => () => engine.destroy(), [engine]);

  return {
    lines: analysis?.lines ?? EMPTY,
    depth: analysis?.depth ?? 0,
    nps: analysis?.nps ?? null,
    running: status === "analyzing" && !(analysis?.finished ?? false),
    status,
    error,
    threaded: engine.threaded,
  };
}
