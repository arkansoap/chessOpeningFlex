import { ResultBar } from "../../components/common";
import { formatEval } from "../../lib/chess";
import { percent } from "../../lib/format";
import type { MoveRow, PositionView } from "../../types";

export interface MovesTableProps {
  position: PositionView;
  onPlay: (san: string) => void;
  /** Choose a move as my repertoire move (my turn only). */
  onChoose: (move: MoveRow) => void;
  busy: boolean;
}

/**
 * What was played from the position. On my turn each row is one of my moves,
 * with what it cost and a star to make it my repertoire move. On the
 * opponent's turn each row is a reply, marked as prepared or not.
 */
export default function MovesTable({ position, onPlay, onChoose, busy }: MovesTableProps) {
  if (position.moves.length === 0) {
    return (
      <p className="muted">
        Aucune de mes parties ne passe par cette position. Joue un coup sur l'échiquier pour
        continuer, ou reviens en arrière.
      </p>
    );
  }
  return (
    <ul className="moves">
      {position.moves.map((move) => (
        <li
          key={move.uci}
          className={`moves__row${move.is_repertoire ? " moves__row--repertoire" : ""}`}
        >
          <button type="button" className="moves__play" onClick={() => onPlay(move.san)}>
            <span className="moves__san">{move.san}</span>
            <span className="moves__count">
              {move.games > 0 ? (
                <>
                  {move.games} <span className="muted">· {percent(move.games, position.games)}</span>
                </>
              ) : (
                <span className="muted">jamais joué</span>
              )}
            </span>
            <span className="moves__bar">
              <ResultBar wins={move.wins} draws={move.draws} losses={move.losses} />
            </span>
            <span className="moves__eval">{formatEval(move.eval)}</span>
            <span className="moves__tags">
              {move.is_best && <span className="tag tag--best">meilleur</span>}
              {move.severity && (
                <span className={`tag tag--${severityClass(move.severity)}`}>{move.severity}</span>
              )}
              {position.my_turn === false &&
                (move.covered ? (
                  <span className="tag tag--ok">prêt : {move.answer}</span>
                ) : (
                  move.games > 0 && <span className="tag tag--todo">à préparer</span>
                ))}
            </span>
          </button>
          {position.my_turn && (
            <button
              type="button"
              className={`moves__star${move.is_repertoire ? " moves__star--on" : ""}`}
              disabled={busy || move.is_repertoire}
              aria-pressed={move.is_repertoire}
              title={
                move.is_repertoire
                  ? "C'est mon coup de répertoire"
                  : `Faire de ${move.san} mon coup de répertoire`
              }
              onClick={() => onChoose(move)}
            >
              {move.is_repertoire ? "★" : "☆"}
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

export function severityClass(severity: string): string {
  return severity === "gaffe" ? "blunder" : severity === "erreur" ? "mistake" : "inaccuracy";
}
