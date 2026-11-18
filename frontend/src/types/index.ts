// Shapes of the API responses, mirroring the backend services.

export type Color = "white" | "black";
export type Platform = "chesscom" | "lichess" | "pgn";
export type MyResult = "win" | "draw" | "loss";
export type Severity = "imprécision" | "erreur" | "gaffe";

export interface AccountInfo {
  username: string;
  last_synced_at: string | null;
}
export type Accounts = Record<"chesscom" | "lichess", AccountInfo | null>;

export interface JobState {
  kind: string;
  status: "idle" | "running" | "done" | "error" | "stopped";
  message: string;
  done: number;
  total: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  result: Record<string, unknown>;
}

export interface GamesSummary {
  games: number;
  by_platform: Partial<Record<Platform, number>>;
  by_color: { white: number; black: number; unknown: number };
  last_played: string | null;
}

export interface GameSummary {
  id: string;
  platform: Platform;
  url: string | null;
  white: string;
  black: string;
  opponent: string | null;
  opponent_elo: number | null;
  my_color: Color | null;
  my_result: MyResult | null;
  result: string;
  time_class: string | null;
  played_at: string | null;
  eco: string | null;
  opening_name: string | null;
}

/** Evaluation from White's point of view. */
export interface Evaluation {
  cp: number | null;
  mate: number | null;
  depth?: number;
}

export interface MoveRow {
  san: string;
  uci: string;
  key_after: string;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  score: number;
  last_played: string | null;
  eval: Evaluation | null;
  // When I am to move:
  is_repertoire?: boolean;
  is_best?: boolean;
  loss?: number | null;
  severity?: Severity | null;
  // When the opponent is to move:
  covered?: boolean;
  answer?: string | null;
}

export interface RepertoireEntry {
  id: string;
  key: string;
  fen: string;
  line: string[];
  move_san: string;
  move_uci: string;
  comment: string | null;
  source: string;
  srs_level: number;
  due_at: string | null;
  last_reviewed_at: string | null;
  reviews: number;
  lapses: number;
  opening?: string | null;
}

export interface PositionView {
  key: string;
  fen: string;
  line: string[];
  color: Color;
  turn: Color;
  my_turn: boolean;
  opening: { eco: string; name: string } | null;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  score: number;
  moves: MoveRow[];
  repertoire: RepertoireEntry | null;
  /** The move that led here when it was mine, and whether it is my repertoire move. */
  last_move: { san: string; uci: string; is_repertoire: boolean; repertoire_move: string | null } | null;
  eval: (Evaluation & { best_san: string | null; best_uci: string | null; pv_san: string | null }) | null;
  recent_games: GameSummary[];
}

export interface OpeningVariation {
  name: string;
  eco: string | null;
  line: string;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  score: number;
  last_played: string | null;
}
export interface OpeningFamily {
  family: string;
  line: string;
  games: number;
  wins: number;
  draws: number;
  losses: number;
  score: number;
  variations: OpeningVariation[];
}

export interface AnalysisStatus {
  engine_available: boolean;
  depth: number;
  total: number;
  pending: number;
  job: JobState;
}

export interface Leak {
  key: string;
  line: string[];
  position_games: number;
  move: Omit<MoveRow, "eval">;
  best_san: string;
  best_uci: string;
  pv_san: string | null;
  severity: Severity;
  weight: number;
  repertoire_move: string | null;
  opening: string | null;
  loss: number;
  loss_cp: number | null;
}

export interface RepertoireData {
  color: Color;
  name: string;
  entries: number;
  new: number;
  due: number;
  levels: Record<string, number>;
  items: RepertoireEntry[];
}

export interface PlayedCount {
  san: string;
  games: number;
}
export interface Gap {
  key: string;
  line: string[];
  games: number;
  played: PlayedCount[];
  last_played: string | null;
  opening: string | null;
}
export interface Deviation extends Gap {
  entry_id: string;
  expected: string;
}
export interface Coverage {
  color: Color;
  games: number;
  covered: number;
  with_deviation: number;
  with_gap: number;
  average_followed: number;
  gaps: Gap[];
  deviations: Deviation[];
}

export interface ReviewItem {
  game: GameSummary;
  status: "covered" | "deviation" | "gap";
  ply: number;
  line: string[];
  played: string | null;
  expected: string | null;
  entry_id: string | null;
  followed: number;
}

export interface DraftAddition {
  key: string;
  line: string[];
  games: number;
  san: string;
  uci: string;
  share: number;
  loss: number | null;
}
export interface DraftSkipped {
  key: string;
  line: string[];
  games: number;
  san: string;
  share: number;
  reason: "hesitation" | "leak" | "not_analysed";
  alternatives?: string[];
  loss?: number;
  best_san?: string;
}
export interface Draft {
  color: Color;
  additions: DraftAddition[];
  skipped: DraftSkipped[];
  added: number;
}

export interface Question {
  entry_id: string;
  color: Color;
  fen: string;
  line: string[];
  srs_level: number;
  is_new: boolean;
}
export interface NextQuestion {
  remaining: number;
  question: Question | null;
}
export interface AnswerResult {
  correct: boolean;
  entry: RepertoireEntry;
}
export interface TrainingStats {
  days: { date: string; reviews: number; correct: number }[];
  colors: Record<Color, { entries: number; new: number; due: number; learned: number }>;
}

export interface LichessMove {
  san: string;
  uci: string;
  games: number;
  white: number;
  draws: number;
  black: number;
  average_rating: number | null;
}
export type LichessStats =
  | { available: false; reason: string }
  | {
      available: true;
      ratings: string;
      games: number;
      white: number;
      draws: number;
      black: number;
      moves: LichessMove[];
    };

/** Which of my games the statistics are computed on. */
export interface Filters {
  timeClasses: string[];
  /** Only games of the last N months; 0 = all. */
  months: number;
}
