import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { Chessboard } from "react-chessboard";
import { Chess, type Square } from "chess.js";

export interface PlayedMove {
  san: string;
  uci: string;
  from: Square;
  to: Square;
}

export interface BoardProps {
  fen: string;
  orientation?: "white" | "black";
  /** Called with a legal move; omit for a display-only board. */
  onMove?: (move: PlayedMove) => void;
  lastMove?: { from: Square; to: Square } | null;
  /** Arrows as [from, to, colour]. */
  arrows?: [Square, Square, string?][];
  /** Extra square backgrounds, e.g. to flash a wrong answer. */
  squareColors?: Record<string, string>;
}

type Promotion = "q" | "r" | "b" | "n";
const PROMOTION_LABELS: Record<Promotion, string> = { q: "Dame", r: "Tour", b: "Fou", n: "Cavalier" };
const PROMOTION_GLYPHS: Record<Promotion, string> = { q: "♛", r: "♜", b: "♝", n: "♞" };

/**
 * Chess board sized by its container. Moves are entered by dragging a piece
 * or, more comfortably on a phone, by tapping it and then its destination.
 * The position is controlled by `fen`: the parent decides what a move does.
 */
export default function Board({
  fen,
  orientation = "white",
  onMove,
  lastMove,
  arrows,
  squareColors,
}: BoardProps) {
  const game = useMemo(() => new Chess(fen), [fen]);
  const [selected, setSelected] = useState<Square | null>(null);
  const [pending, setPending] = useState<{ from: Square; to: Square } | null>(null);
  const interactive = Boolean(onMove);

  // A new position cancels whatever was being entered.
  useEffect(() => {
    setSelected(null);
    setPending(null);
  }, [fen]);

  const targets = useMemo(
    () => (selected ? game.moves({ square: selected, verbose: true }) : []),
    [game, selected]
  );

  const play = useCallback(
    (from: Square, to: Square, promotion?: Promotion): boolean => {
      const candidates = game.moves({ square: from, verbose: true }).filter((m) => m.to === to);
      if (candidates.length === 0) return false;
      if (candidates[0].promotion && !promotion) {
        setPending({ from, to });
        setSelected(null);
        return false;
      }
      const move = candidates.find((m) => !m.promotion || m.promotion === promotion) ?? candidates[0];
      setSelected(null);
      setPending(null);
      onMove?.({ san: move.san, uci: move.lan, from: move.from, to: move.to });
      return true;
    },
    [game, onMove]
  );

  const handleSquareClick = useCallback(
    (square: Square) => {
      if (!interactive) return;
      if (selected && targets.some((m) => m.to === square)) {
        play(selected, square);
        return;
      }
      const piece = game.get(square);
      setSelected(piece && piece.color === game.turn() && square !== selected ? square : null);
    },
    [interactive, selected, targets, play, game]
  );

  const styles: Record<string, CSSProperties> = {};
  if (lastMove) {
    // Colours go through boxShadow so that they layer over the square's own
    // background without fighting the target dots (backgroundImage).
    styles[lastMove.from] = { boxShadow: "inset 0 0 0 100vmax var(--board-last)" };
    styles[lastMove.to] = { boxShadow: "inset 0 0 0 100vmax var(--board-last)" };
  }
  if (selected) {
    styles[selected] = { boxShadow: "inset 0 0 0 100vmax var(--board-selected)" };
    for (const move of targets) {
      styles[move.to] = {
        ...styles[move.to],
        backgroundImage: game.get(move.to)
          ? "radial-gradient(circle, transparent 58%, var(--board-target) 60%)"
          : "radial-gradient(circle, var(--board-target) 22%, transparent 24%)",
      };
    }
  }
  for (const [square, color] of Object.entries(squareColors ?? {})) {
    styles[square] = { ...styles[square], boxShadow: `inset 0 0 0 100vmax ${color}` };
  }

  return (
    <div className="board">
      <Chessboard
        position={fen}
        boardOrientation={orientation}
        arePiecesDraggable={interactive}
        isDraggablePiece={({ piece }) => interactive && piece[0] === game.turn()}
        onPieceDrop={(from, to) => play(from as Square, to as Square)}
        onSquareClick={(square) => handleSquareClick(square as Square)}
        onPieceDragBegin={(_piece, square) => setSelected(square as Square)}
        // Promotions go through our own picker, which also serves taps.
        onPromotionCheck={() => false}
        customSquareStyles={styles}
        customArrows={(arrows ?? []) as never}
        customBoardStyle={{ borderRadius: 6, boxShadow: "var(--shadow)" }}
        customDarkSquareStyle={{ backgroundColor: "var(--board-dark)" }}
        customLightSquareStyle={{ backgroundColor: "var(--board-light)" }}
        animationDuration={160}
      />
      {pending && (
        <div className="board__promotion" role="dialog" aria-label="Choisir la pièce de promotion">
          {(Object.keys(PROMOTION_LABELS) as Promotion[]).map((piece) => (
            <button
              key={piece}
              type="button"
              className="board__promotion-choice"
              title={PROMOTION_LABELS[piece]}
              onClick={() => play(pending.from, pending.to, piece)}
            >
              <span aria-hidden="true">{PROMOTION_GLYPHS[piece]}</span>
              {PROMOTION_LABELS[piece]}
            </button>
          ))}
          <button type="button" className="btn btn--ghost" onClick={() => setPending(null)}>
            Annuler
          </button>
        </div>
      )}
    </div>
  );
}
