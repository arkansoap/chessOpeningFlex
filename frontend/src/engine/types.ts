/** Types shared by the Stockfish worker client and its React bindings. */

/** A single principal variation returned by the engine (one MultiPV slot). */
export interface EngineLine {
  /** 1-based MultiPV rank: 1 is the engine's preferred move. */
  multipv: number;
  /** Search depth this line was last reported at. */
  depth: number;
  /**
   * Centipawn score from *White's* point of view, or `null` when the line ends
   * in a forced mate (see `mate`).
   */
  cp: number | null;
  /**
   * Mate distance in moves from *White's* point of view: positive means White
   * mates, negative means Black mates. `null` when the score is a centipawn
   * evaluation.
   */
  mate: number | null;
  /** Principal variation in UCI notation, e.g. `["e2e4", "e7e5"]`. */
  pvUci: string[];
  /** Same variation rendered in SAN, e.g. `["e4", "e5"]`. */
  pvSan: string[];
  /** SAN of the first move of the line, or `null` if it could not be parsed. */
  moveSan: string | null;
}

export type EngineStatus =
  | "idle"
  | "loading"
  | "ready"
  | "analyzing"
  | "unavailable";

/** Snapshot of an in-progress analysis for one position. */
export interface EngineAnalysis {
  fen: string;
  /** MultiPV lines, sorted by rank (best first). */
  lines: EngineLine[];
  /** Highest depth reached so far. */
  depth: number;
  /** Nodes per second reported by the engine, when known. */
  nps: number | null;
  /** True once the engine has emitted `bestmove` for this position. */
  finished: boolean;
}
