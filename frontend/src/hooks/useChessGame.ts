import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Chess, type Square } from "chess.js";
import { toChessboardPosition } from "../utils/chess";

export interface ChessGameState {
  /** current FEN */
  fen: string;
  /** react-chessboard position object */
  position: Record<string, string>;
  /** side to move: "w" | "b" */
  turn: "w" | "b";
  /** SAN history of moves played */
  history: string[];
  /** true if checkmate / stalemate / draw / insufficient material */
  isGameOver: boolean;
  isCheck: boolean;
}

/**
 * Encapsulates a chess.js game instance and exposes reactive state derived
 * from it. Keeps a single Chess instance in a ref and re-derives the snapshot
 * after each mutation.
 */
export function useChessGame(initialFen?: string) {
  const gameRef = useRef<Chess>(initialFen ? new Chess(initialFen) : new Chess());
  const [snapshot, setSnapshot] = useState<ChessGameState>(() => derive(gameRef.current));

  const refresh = useCallback(() => {
    setSnapshot(derive(gameRef.current));
  }, []);

  const playMove = useCallback(
    (san: string): boolean => {
      try {
        gameRef.current.move(san);
        refresh();
        return true;
      } catch {
        return false;
      }
    },
    [refresh]
  );

  const playFromTo = useCallback(
    (sourceSq: string, targetSq: string, promotion?: string): string | null => {
      try {
        const move = gameRef.current.move({
          from: sourceSq as Square,
          to: targetSq as Square,
          promotion: promotion ?? "q",
        });
        refresh();
        return move.san;
      } catch {
        return null;
      }
    },
    [refresh]
  );

  const undo = useCallback(() => {
    gameRef.current.undo();
    refresh();
  }, [refresh]);

  const reset = useCallback(
    (fen?: string) => {
      gameRef.current = fen ? new Chess(fen) : new Chess();
      refresh();
    },
    [refresh]
  );

  const loadPgn = useCallback(
    (pgn: string): boolean => {
      try {
        gameRef.current.loadPgn(pgn);
        refresh();
        return true;
      } catch {
        return false;
      }
    },
    [refresh]
  );

  // Keep state in sync if the initial FEN changes (e.g. loading a new position).
  useEffect(() => {
    if (initialFen && initialFen !== gameRef.current.fen()) {
      gameRef.current = new Chess(initialFen);
      refresh();
    }
  }, [initialFen, refresh]);

  const api = useMemo(
    () => ({ playMove, playFromTo, undo, reset, loadPgn, refresh }),
    [playMove, playFromTo, undo, reset, loadPgn, refresh]
  );

  return { ...snapshot, ...api, game: gameRef };
}

function derive(game: Chess): ChessGameState {
  return {
    fen: game.fen(),
    position: toChessboardPosition(game),
    turn: game.turn(),
    history: game.history(),
    isGameOver: game.isGameOver(),
    isCheck: game.inCheck(),
  };
}
