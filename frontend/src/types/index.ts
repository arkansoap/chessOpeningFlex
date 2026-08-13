// Shared TypeScript types mirroring backend Pydantic schemas.

export type Color = "white" | "black";

export interface ImportedGame {
  id: string;
  source: string;
  chesscom_username: string | null;
  pgn_file_path: string | null;
  game_id: string;
  white_player: string;
  black_player: string;
  result: string;
  date: string | null;
  eco_code: string | null;
  pgn_data: string;
  is_processed: boolean;
}

export interface Repertoire {
  id: string;
  name: string;
  color: Color;
  description: string | null;
  is_active: boolean;
}

export interface RepertoireLine {
  id: string;
  repertoire_id: string;
  variant_id: string | null;
  moves: string;
  starting_position: string;
  comment: string | null;
  depth: number;
  priority: number;
  last_reviewed: string | null;
}

export interface RepertoireDetail extends Repertoire {
  lines: RepertoireLine[];
}

export interface TrainingQuestion {
  line_id: string;
  fen: string;
  expected_move: string;
  move_number: number;
  color_to_move: Color;
}

export interface TrainingAnswer {
  is_correct: boolean;
  expected_move: string;
  move_played: string;
}

export interface MemorizationStat {
  id: string;
  line_id: string;
  date: string;
  success_rate: number;
  attempts: number;
  last_attempt: string | null;
}

export interface VariantExtracted {
  moves: string;
  starting_position: string;
  eco_code: string | null;
}
