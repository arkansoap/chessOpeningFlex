/** Parsing helpers for Stockfish's UCI output. */
import { Chess } from "chess.js";
import type { EngineLine } from "./types";

/** Everything we can pull out of a single `info ...` line. */
export interface UciInfo {
  depth: number;
  multipv: number;
  cp: number | null;
  mate: number | null;
  nps: number | null;
  pvUci: string[];
}

/**
 * Parses one `info` line emitted during a search.
 *
 * Returns `null` for lines that carry no usable evaluation: `currmove`
 * progress reports, and bound scores (`lowerbound` / `upperbound`) which are
 * partial results of an aborted aspiration window and would make the displayed
 * evaluation jump around.
 */
export function parseInfoLine(line: string): UciInfo | null {
  if (!line.startsWith("info ")) return null;
  if (line.includes("lowerbound") || line.includes("upperbound")) return null;

  const tokens = line.split(/\s+/);
  const pvIndex = tokens.indexOf("pv");
  if (pvIndex === -1) return null;

  const readNumber = (key: string): number | null => {
    const i = tokens.indexOf(key);
    if (i === -1 || i + 1 >= tokens.length || i > pvIndex) return null;
    const value = Number(tokens[i + 1]);
    return Number.isFinite(value) ? value : null;
  };

  const depth = readNumber("depth");
  if (depth === null) return null;

  const scoreIndex = tokens.indexOf("score");
  let cp: number | null = null;
  let mate: number | null = null;
  if (scoreIndex !== -1 && scoreIndex < pvIndex) {
    const kind = tokens[scoreIndex + 1];
    const value = Number(tokens[scoreIndex + 2]);
    if (Number.isFinite(value)) {
      if (kind === "cp") cp = value;
      else if (kind === "mate") mate = value;
    }
  }
  if (cp === null && mate === null) return null;

  const pvUci = tokens.slice(pvIndex + 1).filter(Boolean);
  if (pvUci.length === 0) return null;

  return {
    depth,
    multipv: readNumber("multipv") ?? 1,
    cp,
    mate,
    nps: readNumber("nps"),
    pvUci,
  };
}

/**
 * Converts a UCI principal variation to SAN by replaying it from `fen`.
 * Stops at the first move chess.js rejects, so a truncated or slightly stale
 * PV still renders the part that is valid.
 */
export function pvToSan(fen: string, pvUci: string[]): string[] {
  let board: Chess;
  try {
    board = new Chess(fen);
  } catch {
    return [];
  }
  const san: string[] = [];
  for (const uci of pvUci) {
    const from = uci.slice(0, 2);
    const to = uci.slice(2, 4);
    const promotion = uci.length > 4 ? uci[4] : undefined;
    try {
      const move = board.move({ from, to, promotion: promotion ?? "q" });
      san.push(move.san);
    } catch {
      break;
    }
  }
  return san;
}

/**
 * Turns a parsed `info` line into a display-ready {@link EngineLine},
 * flipping the score to White's point of view (the engine reports it from the
 * side to move).
 */
export function toEngineLine(fen: string, info: UciInfo): EngineLine {
  const blackToMove = fen.split(" ")[1] === "b";
  const sign = blackToMove ? -1 : 1;
  const pvSan = pvToSan(fen, info.pvUci);
  return {
    multipv: info.multipv,
    depth: info.depth,
    cp: info.cp === null ? null : info.cp * sign,
    mate: info.mate === null ? null : info.mate * sign,
    pvUci: info.pvUci,
    pvSan,
    moveSan: pvSan[0] ?? null,
  };
}

/**
 * Formats a score for display, always from White's point of view:
 * `+0.32`, `-1.05`, `M3`, `-M2`.
 */
export function formatScore(line: Pick<EngineLine, "cp" | "mate">): string {
  if (line.mate !== null) {
    return `${line.mate < 0 ? "-" : "+"}M${Math.abs(line.mate)}`;
  }
  if (line.cp === null) return "—";
  const pawns = line.cp / 100;
  return `${pawns >= 0 ? "+" : "−"}${Math.abs(pawns).toFixed(2)}`;
}

/**
 * Maps a score onto the 0..1 range used by the evaluation bar, where 1 is
 * winning for White. Uses the same logistic squashing as common chess UIs so
 * that small advantages stay readable and huge ones saturate.
 */
export function scoreToWhiteShare(line: Pick<EngineLine, "cp" | "mate">): number {
  if (line.mate !== null) return line.mate > 0 ? 1 : 0;
  if (line.cp === null) return 0.5;
  const clamped = Math.max(-1000, Math.min(1000, line.cp));
  return 1 / (1 + Math.exp(-clamped / 350));
}

/**
 * Renders a PV as a move list with correct numbering for the position it
 * starts from, e.g. `12...Nf6 13.Bd3 O-O`.
 */
export function formatPv(fen: string, pvSan: string[], maxPlies = 12): string {
  const parts = fen.split(" ");
  const blackToMove = parts[1] === "b";
  let moveNumber = Number(parts[5]);
  if (!Number.isFinite(moveNumber) || moveNumber < 1) moveNumber = 1;

  const out: string[] = [];
  let isBlack = blackToMove;
  pvSan.slice(0, maxPlies).forEach((san, i) => {
    if (!isBlack) {
      out.push(`${moveNumber}.${san}`);
    } else if (i === 0) {
      out.push(`${moveNumber}...${san}`);
    } else {
      out.push(san);
    }
    if (isBlack) moveNumber += 1;
    isBlack = !isBlack;
  });
  return out.join(" ") + (pvSan.length > maxPlies ? " …" : "");
}
