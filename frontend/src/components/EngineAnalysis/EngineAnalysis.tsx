import { useEffect, useState } from "react";
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
  /** Whether analysis is on the first time the user ever opens the panel. */
  defaultEnabled?: boolean;
}

/** Key under which the on/off choice is remembered between visits. */
const STORAGE_KEY = "chessopeningflex.engine.enabled";

function readStoredEnabled(fallback: boolean): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === null ? fallback : stored === "true";
  } catch {
    // Private browsing and blocked site data both throw here.
    return fallback;
  }
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
  // Remembered across visits: someone who turned the engine off to save
  // battery should not find it running again on the next page.
  const [enabled, setEnabled] = useState(() => readStoredEnabled(defaultEnabled));

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(enabled));
    } catch {
      // Not being able to remember the choice is not worth failing over.
    }
  }, [enabled]);
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
        <button
          type="button"
          className={`engine-toggle${enabled ? " engine-toggle--on" : ""}`}
          onClick={() => setEnabled((on) => !on)}
          disabled={unavailable}
          aria-pressed={enabled}
          title={
            enabled
              ? "Arrêter l'analyse et libérer le moteur"
              : "Lancer l'analyse de la position"
          }
        >
          <span aria-hidden="true">{enabled ? "⏸" : "▶"}</span>
          {enabled ? "Analyse activée" : "Activer l'analyse"}
        </button>
        <span className="engine-analysis__meta">
          {unavailable
            ? "indisponible"
            : !enabled
              ? "désactivée"
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
              Analyse désactivée : le moteur est déchargé et ne consomme ni
              processeur ni mémoire.
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

      {/* Attribution and licence link: the GPL-3.0 engine is served to every
          visitor, so its notice travels with it. See THIRD-PARTY.md. */}
      {!unavailable && (
        <footer className="engine-analysis__footer">
          <a
            href="https://github.com/official-stockfish/Stockfish"
            target="_blank"
            rel="noreferrer"
          >
            Stockfish 18
          </a>{" "}
          lite (
          <a href="/stockfish/LICENSE.txt" target="_blank" rel="noreferrer">
            GPL-3.0
          </a>
          ) · {threaded ? "multi-thread" : "mono-thread"}
          {enabled && nps ? ` · ${(nps / 1000).toFixed(0)} kN/s` : ""}
        </footer>
      )}
    </section>
  );
}
