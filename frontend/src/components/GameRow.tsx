import type { ReactNode } from "react";
import { PLATFORM_LABELS, TIME_CLASS_LABELS, formatDate } from "../lib/format";
import type { GameSummary } from "../types";

const RESULT_LABELS = { win: "Gain", draw: "Nulle", loss: "Défaite" } as const;

/** One of my games: opponent, result, date, and a link to the site. */
export default function GameRow({ game, children }: { game: GameSummary; children?: ReactNode }) {
  return (
    <li className="game-row">
      <div className="game-row__main">
        {game.my_result && (
          <span className={`result result--${game.my_result}`}>{RESULT_LABELS[game.my_result]}</span>
        )}
        <span className="game-row__opponent">
          {game.opponent ?? `${game.white} – ${game.black}`}
          {game.opponent_elo ? <span className="muted"> ({game.opponent_elo})</span> : null}
        </span>
        <span className="muted game-row__meta">
          {[
            formatDate(game.played_at),
            game.time_class ? TIME_CLASS_LABELS[game.time_class] : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
        {game.url && (
          <a className="game-row__link" href={game.url} target="_blank" rel="noreferrer">
            {PLATFORM_LABELS[game.platform]} ↗
          </a>
        )}
      </div>
      {children && <div className="game-row__detail">{children}</div>}
    </li>
  );
}
