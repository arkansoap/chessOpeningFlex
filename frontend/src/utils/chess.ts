import { Chess, type Square, type PieceSymbol, type Color } from "chess.js";

/**
 * Converts a chess.js board state into the position object expected by
 * react-chessboard v4: { [square]: piece } where piece is like "wP".
 */
export function toChessboardPosition(
  game: Chess
): Record<string, string> {
  const position: Record<string, string> = {};
  const board = game.board();
  for (let rankIndex = 0; rankIndex < 8; rankIndex++) {
    const row = board[rankIndex];
    for (let fileIndex = 0; fileIndex < 8; fileIndex++) {
      const piece = row[fileIndex];
      if (piece) {
        const file = "abcdefgh"[fileIndex];
        const rank = 8 - rankIndex;
        const square = `${file}${rank}` as Square;
        position[square] = `${piece.color}${piece.type}`;
      }
    }
  }
  return position;
}

export function squareToCoords(square: Square): [number, number] {
  const file = square.charCodeAt(0) - "a".charCodeAt(0);
  const rank = Number(square[1]) - 1;
  return [file, rank];
}

export type { Square, PieceSymbol, Color };
