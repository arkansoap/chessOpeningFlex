import { useEffect, useState } from "react";
import { numberedMove } from "../../lib/chess";
import { errorMessage, repertoire as repertoireApi } from "../../services/api";
import type { PositionView } from "../../types";

/** My repertoire move in the current position, with its note. */
export default function RepertoireBox({
  position,
  onChanged,
  onAdoptLast,
}: {
  position: PositionView;
  onChanged: () => void;
  /** Make the move that led to this position my repertoire move. */
  onAdoptLast: () => void;
}) {
  const entry = position.repertoire;
  const [note, setNote] = useState(entry?.comment ?? "");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setNote(entry?.comment ?? "");
    setError(null);
  }, [entry?.id, entry?.comment]);

  if (!position.my_turn) {
    // After a move of mine: offer to make it my repertoire move. This is how
    // a move I have never played in a game enters the repertoire.
    const last = position.last_move;
    if (!last) return null;
    const label = numberedMove(last.san, position.line.length - 1);
    if (last.is_repertoire) {
      return (
        <div className="rep-box">
          <span>
            ★ <strong>{label}</strong> est mon coup de répertoire.
          </span>
        </div>
      );
    }
    return (
      <div className="rep-box rep-box--empty rep-box--action">
        <span>
          {last.repertoire_move
            ? `Mon coup de répertoire ici est ${last.repertoire_move}.`
            : "Pas encore de coup de répertoire avant ce coup."}
        </span>
        <button type="button" className="btn btn--small" onClick={onAdoptLast}>
          ☆ {last.repertoire_move ? `Le remplacer par ${label}` : `Choisir ${label}`}
        </button>
      </div>
    );
  }
  if (!entry) {
    return (
      <div className="rep-box rep-box--empty">
        Pas encore de coup de répertoire ici : touche ☆ à côté d'un coup pour le choisir.
      </div>
    );
  }

  const chosen = position.moves.find((m) => m.is_repertoire);
  const saveNote = async () => {
    if (note === (entry.comment ?? "")) return;
    try {
      await repertoireApi.setComment(entry.id, note);
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    }
  };
  const remove = async () => {
    try {
      await repertoireApi.remove(entry.id);
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="rep-box">
      <div className="rep-box__head">
        <span>
          ★ Mon coup : <strong>{numberedMove(entry.move_san, position.line.length)}</strong>
        </span>
        <button type="button" className="btn btn--ghost btn--small" onClick={() => void remove()}>
          Retirer
        </button>
      </div>
      {chosen?.severity && (
        <p className="rep-box__warning">
          Le moteur le juge comme une {chosen.severity}
          {position.eval?.best_san ? ` : il préfère ${position.eval.best_san}.` : "."}
        </p>
      )}
      <textarea
        className="rep-box__note"
        rows={2}
        placeholder="Note : l'idée, le plan, le piège à connaître…"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        onBlur={() => void saveNote()}
      />
      {error && <p className="error">{error}</p>}
    </div>
  );
}
