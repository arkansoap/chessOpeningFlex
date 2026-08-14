import { useState } from "react";
import { chesscom } from "../../services/api";
import type { ImportedGame } from "../../types";

export interface ChessComImporterProps {
  onImported?: (games: ImportedGame[]) => void;
}

const TIME_CONTROLS = [
  { label: "Tous", value: "" },
  { label: "Rapide", value: "rapid" },
  { label: "Blitz", value: "blitz" },
  { label: "Balle", value: "bullet" },
  { label: "Quotidienne", value: "daily" },
];

/**
 * Form to import games from the chess.com public API by username + optional
 * filters (time control, date range as YYYY-MM).
 */
export default function ChessComImporter({ onImported }: ChessComImporterProps) {
  const [username, setUsername] = useState("");
  const [timeControl, setTimeControl] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError("Veuillez saisir un nom d'utilisateur.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const filters: Record<string, string> = {};
      if (timeControl) filters.time_control = timeControl;
      if (startDate) filters.start_date = startDate;
      if (endDate) filters.end_date = endDate;
      const games = await chesscom.importGames(username.trim(), filters);
      onImported?.(games);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="chesscom-importer">
      <h3>Importer depuis chess.com</h3>
      <label>
        Nom d'utilisateur&nbsp;
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="ex : hikaru"
        />
      </label>

      <label>
        Cadence&nbsp;
        <select
          value={timeControl}
          onChange={(e) => setTimeControl(e.target.value)}
        >
          {TIME_CONTROLS.map((tc) => (
            <option key={tc.value} value={tc.value}>
              {tc.label}
            </option>
          ))}
        </select>
      </label>

      <div style={{ display: "flex", gap: "1rem" }}>
        <label>
          Début (AAAA-MM)&nbsp;
          <input
            type="month"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </label>
        <label>
          Fin (AAAA-MM)&nbsp;
          <input
            type="month"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </label>
      </div>

      <button type="submit" disabled={loading}>
        {loading ? "Import en cours…" : "Importer"}
      </button>
      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}
    </form>
  );
}

function messageFromError(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? "Échec de l'import.";
  }
  return "Échec de l'import.";
}
