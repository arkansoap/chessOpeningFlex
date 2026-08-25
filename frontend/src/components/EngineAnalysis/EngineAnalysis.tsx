import { useState } from "react";
import { useChessEngine } from "../../hooks/useChessEngine";
import { formatPv, formatScore } from "../../engine/uci";
import EvalBar from "./EvalBar";

export interface EngineAnalysisProps {
  /** Position to evaluate. `null` leaves the engine idle. */
  fen: string | null;
  /** Number of principal variations to show. */
  multiPv?: number;
  /** Depth at which the search stops refining. */
  maxDepth?: number;
  /** Height of the evaluation bar; match the board's height. */
  height?: number;
  /** Whether analysis is on when the component first mounts. */
  defaultEnabled?: boolean;
}

/**
 * Live engine evaluation of a position: an evaluation bar plus the engine's
 * top lines, refreshed as the search deepens.
 *
 * Designed to sit next to a board — when the board's position changes the
 * analysis restarts on its own.
 */
export default function EngineAnalysis({
  fen,
  multiPv = 5,
  maxDepth = 20,
  height = 420,
  defaultEnabled = true,
}: EngineAnalysisProps) {
  const [enabled, setEnabled] = useState(defaultEnabled);
  const { lines, depth, nps, running, status, error, threaded } = useChessEngine({
    fen,
    enabled,
    multiPv,
    maxDepth,
  });

  const best = lines[0] ?? null;
  const unavailable = status === "unavailable";

  return (
    <section className="engine-analysis" aria-label="Analyse du moteur">
      <header className="engine-analysis__header">
        <label className="engine-analysis__toggle">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            disabled={unavailable}
          />
          Moteur
        </label>
        <span className="engine-analysis__meta">
          {unavailable
            ? "indisponible"
            : !enabled
              ? "en pause"
              : status === "loading"
                ? "chargement…"
                : `profondeur ${depth}/${maxDepth}${running ? " …" : ""}`}
        </span>
      </header>

      <div className="engine-analysis__body">
        <EvalBar line={enabled && !unavailable ? best : null} height={height} />

        <ol className="engine-lines" style={{ maxHeight: height }}>
          {unavailable && (
            <li className="engine-lines__empty">
              Moteur indisponible.
              <br />
              <code>npm run engine:fetch</code> puis recharger la page.
              {error && (
                <span className="engine-lines__error" title={error}>
                  {error}
                </span>
              )}
            </li>
          )}

          {!unavailable && !enabled && (
            <li className="engine-lines__empty">
              Analyse en pause. Cochez « Moteur » pour la relancer.
            </li>
          )}

          {!unavailable && enabled && lines.length === 0 && (
            <li className="engine-lines__empty">
              {fen ? "Analyse en cours…" : "Aucune position à analyser."}
            </li>
          )}

          {!unavailable &&
            enabled &&
            fen &&
            lines.map((line) => (
              <li key={line.multipv} className="engine-lines__row">
                <span
                  className={`engine-lines__score${
                    (line.mate ?? line.cp ?? 0) < 0
                      ? " engine-lines__score--black"
                      : ""
                  }`}
                >
                  {formatScore(line)}
                </span>
                <span className="engine-lines__pv" title={formatPv(fen, line.pvSan, 40)}>
                  {formatPv(fen, line.pvSan)}
                </span>
              </li>
            ))}
        </ol>
      </div>

      {!unavailable && enabled && (
        <footer className="engine-analysis__footer">
          Stockfish 18 lite · {threaded ? "multi-thread" : "mono-thread"}
          {nps ? ` · ${(nps / 1000).toFixed(0)} kN/s` : ""}
        </footer>
      )}
    </section>
  );
}
