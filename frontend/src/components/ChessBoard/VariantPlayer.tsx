import { useCallback, useEffect, useState } from "react";
import { Chessboard } from "react-chessboard";
import { useChessGame } from "../../hooks/useChessGame";

export interface VariantPlayerProps {
  /** Space-separated SAN moves, e.g. "e4 e5 Nf3 Nc6 Bb5" */
  moves: string;
  /** FEN of the starting position (defaults to the initial position). */
  startingFen?: string;
  /** Orientation of the board. */
  orientation?: "white" | "black";
}

/**
 * Read-only board that replays a variant move by move with prev/next controls.
 * Used to preview an extracted line on the board instead of just showing the
 * starting position.
 */
export default function VariantPlayer({
  moves,
  startingFen,
  orientation = "white",
}: VariantPlayerProps) {
  const game = useChessGame(startingFen);
  const sanMoves = moves.split(" ").filter(Boolean);
  // Index of the last move applied. -1 means the starting position.
  const [step, setStep] = useState(-1);

  // Reset to the starting position whenever the variant changes.
  useEffect(() => {
    game.reset(startingFen);
    setStep(-1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moves, startingFen]);

  const goTo = useCallback(
    (targetStep: number) => {
      const clamped = Math.max(-1, Math.min(targetStep, sanMoves.length - 1));
      // Reset and replay up to the target step.
      game.reset(startingFen);
      for (let i = 0; i <= clamped; i++) {
        if (!game.playMove(sanMoves[i])) {
          // Stop on the first illegal move.
          setStep(i - 1);
          return;
        }
      }
      setStep(clamped);
    },
    [game, sanMoves, startingFen]
  );

  const next = useCallback(() => goTo(step + 1), [goTo, step]);
  const prev = useCallback(() => goTo(step - 1), [goTo, step]);

  const moveNumber = Math.floor((step + 1) / 2) + 1;
  const isWhiteToMove = (step + 1) % 2 === 0;

  return (
    <div className="variant-player">
      <div style={{ maxWidth: 420 }}>
        <Chessboard
          position={game.position}
          arePiecesDraggable={false}
          boardOrientation={orientation}
        />
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          marginTop: "0.5rem",
          flexWrap: "wrap",
        }}
      >
        <button type="button" onClick={prev} disabled={step < 0} title="Coup précédent">
          ◀
        </button>
        <span style={{ minWidth: 140, textAlign: "center", fontFamily: "monospace" }}>
          {step < 0
            ? "Position de départ"
            : `${moveNumber}.${isWhiteToMove ? "" : ".."} ${sanMoves[step]}`}
        </span>
        <button
          type="button"
          onClick={next}
          disabled={step >= sanMoves.length - 1}
          title="Coup suivant"
        >
          ▶
        </button>
        <button
          type="button"
          onClick={() => goTo(-1)}
          disabled={step < 0}
          style={{ marginLeft: "0.5rem" }}
          title="Revenir au début"
        >
          ⏮
        </button>
        <button
          type="button"
          onClick={() => goTo(sanMoves.length - 1)}
          disabled={step >= sanMoves.length - 1}
          title="Aller à la fin"
        >
          ⏭
        </button>
        <span style={{ marginLeft: "0.5rem", color: "#6b7280" }}>
          {step + 1}/{sanMoves.length} coups
        </span>
      </div>

      <p style={{ fontFamily: "monospace", marginTop: "0.5rem" }}>
        {sanMoves.join(" ")}
      </p>
    </div>
  );
}
