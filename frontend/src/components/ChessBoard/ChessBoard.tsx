import { useCallback } from "react";
import { Chessboard } from "react-chessboard";
import { useChessGame } from "../../hooks/useChessGame";

export interface ChessBoardProps {
  /** FEN to display. If omitted, the initial position is used. */
  fen?: string;
  /** Orientation: "white" (default) or "black". */
  orientation?: "white" | "black";
  /** When false, pieces cannot be dragged (display-only). */
  interactive?: boolean;
  /**
   * Called with the SAN of a successfully played move. If the callback
   * returns false the move is rolled back (useful for training validation).
   */
  onMove?: (san: string, fen: string) => boolean | void;
  /** Highlight squares (e.g. last move or hint). */
  highlightSquares?: string[];
  /** Force a specific position object instead of deriving from internal state. */
  position?: Record<string, string>;
}

/**
 * Reusable interactive chess board. Wraps react-chessboard and keeps an
 * internal chess.js game for move validation. The parent is notified through
 * `onMove` and may veto a move by returning false.
 */
export default function ChessBoard({
  fen,
  orientation = "white",
  interactive = true,
  onMove,
  highlightSquares = [],
  position,
}: ChessBoardProps) {
  const game = useChessGame(fen);

  const handlePieceDrop = useCallback(
    (sourceSq: string, targetSq: string, piece: string): boolean => {
      if (!interactive) return false;
      const isPawn = piece[1] === "p" || piece[1] === "P";
      const targetRank = Number(targetSq[1]);
      const willPromote = isPawn && (targetRank === 8 || targetRank === 1);
      const san = game.playFromTo(
        sourceSq,
        targetSq,
        willPromote ? "q" : undefined
      );
      if (!san) return false;
      const accepted = onMove?.(san, game.fen);
      if (accepted === false) {
        game.undo();
        return false;
      }
      return true;
    },
    [game, interactive, onMove]
  );

  const currentPosition = position ?? game.position;

  const squareStyles: Record<string, React.CSSProperties> = {};
  for (const sq of highlightSquares) {
    squareStyles[sq] = {
      background:
        "radial-gradient(circle, rgba(255,255,0,0.8) 0%, rgba(255,255,0,0.2) 70%)",
    };
  }

  return (
    <div className="chessboard-container" style={{ maxWidth: 480 }}>
      <Chessboard
        position={currentPosition}
        onPieceDrop={handlePieceDrop}
        arePiecesDraggable={interactive}
        boardOrientation={orientation}
        customSquareStyles={squareStyles}
      />
    </div>
  );
}
