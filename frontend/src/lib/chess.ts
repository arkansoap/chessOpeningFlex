import { Chess, type Square } from "chess.js";
import type { Evaluation } from "../types";

export interface LinePosition {
  fen: string;
  /** Squares of the last move, to highlight it. */
  lastMove: { from: Square; to: Square } | null;
  /** How many moves of the line could be played. */
  played: number;
}

/** Position reached by a list of SAN moves from the start. */
export function positionOf(line: string[]): LinePosition {
  const game = new Chess();
  let lastMove: LinePosition["lastMove"] = null;
  let played = 0;
  for (const san of line) {
    try {
      const move = game.move(san);
      lastMove = { from: move.from, to: move.to };
      played += 1;
    } catch {
      break;
    }
  }
  return { fen: game.fen(), lastMove, played };
}

/** "1. e4 e5 2. Nf3" from ["e4", "e5", "Nf3"]. */
export function numbered(line: string[]): string {
  return line
    .map((san, i) => (i % 2 === 0 ? `${i / 2 + 1}. ${san}` : san))
    .join(" ");
}

/** A move with its number, as it reads after `ply` moves: "3. Bb5" or "2… Nc6". */
export function numberedMove(san: string, ply: number): string {
  const moveNumber = Math.floor(ply / 2) + 1;
  return ply % 2 === 0 ? `${moveNumber}. ${san}` : `${moveNumber}… ${san}`;
}

/** Line as a URL parameter and back. */
export const lineToParam = (line: string[]): string => line.join(" ");
export const paramToLine = (param: string | null): string[] =>
  (param ?? "").split(/\s+/).filter(Boolean);

/** Link to the explorer at a position. */
export function explorerLink(line: string[]): string {
  const query = line.length > 0 ? `?line=${encodeURIComponent(lineToParam(line))}` : "";
  return `/ouvertures${query}`;
}

/** "+0.8", "-1.2", "#3": evaluation from White's side, in pawns. */
export function formatEval(evaluation: Evaluation | null | undefined): string {
  if (!evaluation) return "";
  if (evaluation.mate !== null && evaluation.mate !== undefined) {
    return `#${evaluation.mate}`;
  }
  if (evaluation.cp === null || evaluation.cp === undefined) return "";
  const pawns = evaluation.cp / 100;
  return `${pawns > 0 ? "+" : ""}${pawns.toFixed(1)}`;
}

/** UCI move ("e2e4") as board squares. */
export function squaresOf(uci: string): [Square, Square] {
  return [uci.slice(0, 2) as Square, uci.slice(2, 4) as Square];
}
