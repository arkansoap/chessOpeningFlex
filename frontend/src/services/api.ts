import axios from "axios";
import type {
  ImportedGame,
  MemorizationStat,
  Repertoire,
  RepertoireDetail,
  RepertoireLine,
  TrainingAnswer,
  TrainingQuestion,
  VariantExtracted,
} from "../types";

const client = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// --- chess.com -----------------------------------------------------------

export const chesscom = {
  importGames: (username: string, filters?: Record<string, string>) =>
    client
      .post<ImportedGame[]>("/chesscom/import", { username, ...filters })
      .then((r) => r.data),
  uploadPgn: (pgn: string) =>
    client
      .post<ImportedGame[]>("/chesscom/upload-pgn", pgn, {
        headers: { "Content-Type": "text/plain" },
      })
      .then((r) => r.data),
};

// --- analysis -----------------------------------------------------------

export const analysis = {
  variants: (pgn: string, color = "white", minDepth = 0) =>
    client
      .post<VariantExtracted[]>("/analysis/variants", {
        pgn,
        color,
        min_depth: minDepth,
      })
      .then((r) => r.data),
  evaluate: (fen: string, depth?: number) =>
    client
      .post("/analysis/evaluate", { fen, depth })
      .then((r) => r.data),
};

// --- repertoire ---------------------------------------------------------

export const repertoire = {
  list: () => client.get<Repertoire[]>("/repertoire").then((r) => r.data),
  get: (id: string) =>
    client.get<RepertoireDetail>(`/repertoire/${id}`).then((r) => r.data),
  create: (data: { name: string; color: string; description?: string }) =>
    client.post<Repertoire>("/repertoire", data).then((r) => r.data),
  update: (id: string, data: Partial<Repertoire>) =>
    client.put<Repertoire>(`/repertoire/${id}`, data).then((r) => r.data),
  remove: (id: string) => client.delete(`/repertoire/${id}`),
  addLine: (data: {
    repertoire_id: string;
    moves: string;
    starting_position?: string;
    depth?: number;
  }) => client.post<RepertoireLine>("/repertoire/line", data).then((r) => r.data),
  updateLine: (id: string, data: Partial<RepertoireLine>) =>
    client.put<RepertoireLine>(`/repertoire/line/${id}`, data).then((r) => r.data),
  removeLine: (id: string) => client.delete(`/repertoire/line/${id}`),
};

// --- training -----------------------------------------------------------

export const training = {
  getQuestion: (params: {
    line_id: string;
    mode?: string;
    step?: number;
  }) => client.get<TrainingQuestion>("/training/question", { params }).then((r) => r.data),
  submitAnswer: (data: {
    line_id: string;
    move_played: string;
    expected_move: string;
    fen: string;
  }) => client.post<TrainingAnswer>("/training/answer", data).then((r) => r.data),
  recordSession: (params: {
    repertoire_id: string;
    line_id: string;
    mode?: string;
    total_questions: number;
    correct_answers: number;
    time_spent?: number;
    score?: number;
  }) => client.post("/training/session", null, { params }).then((r) => r.data),
  stats: (params: { repertoire_id?: string; line_id?: string }) =>
    client.get<MemorizationStat[]>("/training/stats", { params }).then((r) => r.data),
};
