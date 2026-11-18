import axios from "axios";
import type {
  Accounts,
  AnalysisStatus,
  AnswerResult,
  Color,
  Coverage,
  Draft,
  Filters,
  GamesSummary,
  JobState,
  Leak,
  LichessStats,
  NextQuestion,
  OpeningFamily,
  PositionView,
  RepertoireData,
  RepertoireEntry,
  ReviewItem,
  TrainingStats,
} from "../types";

const client = axios.create({ baseURL: "/api/v1" });

/** Human-readable message of a failed request. */
export function errorMessage(error: unknown, fallback = "Une erreur est survenue."): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (!error.response) return "Serveur injoignable.";
  }
  return fallback;
}

/** Query parameters selecting my games: colour plus the active filters. */
export function gameParams(color: Color, filters: Filters): Record<string, string> {
  const params: Record<string, string> = { color };
  if (filters.timeClasses.length > 0) params.time_class = filters.timeClasses.join(",");
  if (filters.months > 0) {
    const since = new Date();
    since.setMonth(since.getMonth() - filters.months);
    params.since = since.toISOString().slice(0, 10);
  }
  return params;
}

const PGN_HEADERS = { headers: { "Content-Type": "text/plain" } };

export const games = {
  accounts: () => client.get<Accounts>("/accounts").then((r) => r.data),
  setAccounts: (data: { chesscom?: string; lichess?: string }) =>
    client.put<Accounts>("/accounts", data).then((r) => r.data),
  sync: (months?: number) =>
    client.post<JobState>("/sync", { months: months || null }).then((r) => r.data),
  syncStatus: () => client.get<JobState>("/sync/status").then((r) => r.data),
  stopSync: () => client.post<JobState>("/sync/stop").then((r) => r.data),
  summary: () => client.get<GamesSummary>("/games/summary").then((r) => r.data),
  uploadPgn: (pgn: string, player?: string) =>
    client
      .post<{ found: number; imported: number; unknown_side: number; deviations: number }>(
        "/games/upload-pgn",
        pgn,
        { ...PGN_HEADERS, params: player ? { player } : {} }
      )
      .then((r) => r.data),
};

export const explorer = {
  position: (color: Color, filters: Filters, line: string[], signal?: AbortSignal) =>
    client
      .get<PositionView>("/explorer/position", {
        params: { ...gameParams(color, filters), line: line.join(" ") },
        signal,
      })
      .then((r) => r.data),
  openings: (color: Color, filters: Filters) =>
    client
      .get<OpeningFamily[]>("/explorer/openings", { params: gameParams(color, filters) })
      .then((r) => r.data),
  lichess: (line: string[], rating: number) =>
    client
      .get<LichessStats>("/explorer/lichess", { params: { line: line.join(" "), rating } })
      .then((r) => r.data),
};

export const analysis = {
  status: () => client.get<AnalysisStatus>("/analysis/status").then((r) => r.data),
  run: () => client.post<JobState>("/analysis/run", {}).then((r) => r.data),
  stop: () => client.post<JobState>("/analysis/stop").then((r) => r.data),
  leaks: (color: Color, filters: Filters, minLoss: number, minGames: number) =>
    client
      .get<{ total: number; leaks: Leak[] }>("/leaks", {
        params: { ...gameParams(color, filters), min_loss: minLoss, min_games: minGames },
      })
      .then((r) => r.data),
};

export const repertoire = {
  get: (color: Color) => client.get<RepertoireData>(`/repertoire/${color}`).then((r) => r.data),
  setMove: (color: Color, line: string[], move: string, source = "manual") =>
    client
      .put<RepertoireEntry>(`/repertoire/${color}/entry`, { line: line.join(" "), move, source })
      .then((r) => r.data),
  setComment: (entryId: string, comment: string) =>
    client.patch<RepertoireEntry>(`/repertoire/entry/${entryId}`, { comment }).then((r) => r.data),
  remove: (entryId: string) => client.delete(`/repertoire/entry/${entryId}`),
  coverage: (color: Color, filters: Filters) =>
    client
      .get<Coverage>("/repertoire/coverage", { params: gameParams(color, filters) })
      .then((r) => r.data),
  review: (color: Color, limit = 30) =>
    client.get<ReviewItem[]>(`/repertoire/${color}/review`, { params: { limit } }).then((r) => r.data),
  draft: (
    color: Color,
    filters: Filters,
    options: { min_games: number; min_share: number; max_loss: number; dry_run: boolean }
  ) =>
    client
      .post<Draft>("/repertoire/adopt", options, { params: gameParams(color, filters) })
      .then((r) => r.data),
  exportUrl: (color: Color) => `/api/v1/repertoire/${color}/export.pgn`,
  importPgn: (color: Color, pgn: string, overwrite: boolean) =>
    client
      .post<{ added: number; updated: number; kept: number }>(
        `/repertoire/${color}/import-pgn`,
        pgn,
        { ...PGN_HEADERS, params: { overwrite } }
      )
      .then((r) => r.data),
};

export const training = {
  next: (color: Color | "any", mode: "due" | "all", exclude?: string) =>
    client
      .get<NextQuestion>("/training/next", { params: { color, mode, exclude } })
      .then((r) => r.data),
  answer: (entryId: string, move: string, reveal = false) =>
    client
      .post<AnswerResult>("/training/answer", { entry_id: entryId, move, reveal })
      .then((r) => r.data),
  stats: () => client.get<TrainingStats>("/training/stats").then((r) => r.data),
};
