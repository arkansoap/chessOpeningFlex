import { useEffect, useState } from "react";
import VariantPlayer from "../ChessBoard/VariantPlayer";
import { repertoire as repertoireApi } from "../../services/api";
import type { RepertoireLine } from "../../types";

export interface LineEditorProps {
  line: RepertoireLine;
  onUpdated?: (line: RepertoireLine) => void;
  onDeleted?: (lineId: string) => void;
}

/**
 * Editor for a single repertoire line: shows the moves on a board and lets
 * the user edit the comment, depth (move count), priority, and delete it.
 */
export default function LineEditor({
  line,
  onUpdated,
  onDeleted,
}: LineEditorProps) {
  const [comment, setComment] = useState(line.comment ?? "");
  const [depth, setDepth] = useState(line.depth);
  const [priority, setPriority] = useState(line.priority);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setComment(line.comment ?? "");
    setDepth(line.depth);
    setPriority(line.priority);
  }, [line.id]);

  const plies = line.moves.split(" ").filter(Boolean);
  const displayMoves = plies.slice(0, depth).join(" ");

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await repertoireApi.updateLine(line.id, {
        comment,
        depth,
        priority,
      });
      onUpdated?.(updated);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    setSaving(true);
    setError(null);
    try {
      await repertoireApi.removeLine(line.id);
      onDeleted?.(line.id);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="line-editor" style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
      <div>
        <VariantPlayer moves={displayMoves} startingFen={line.starting_position} />
      </div>

      <div style={{ flex: 1, minWidth: 280 }}>
        <h3>Édition de la ligne</h3>

        <label>
          Profondeur (coups)&nbsp;
          <input
            type="range"
            min={1}
            max={plies.length}
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          />
          <span>{depth}</span>
        </label>

        <div style={{ marginTop: "0.5rem" }}>
          <label>
            Priorité&nbsp;
            <input
              type="number"
              value={priority}
              onChange={(e) => setPriority(Number(e.target.value))}
            />
          </label>
        </div>

        <div style={{ marginTop: "0.5rem" }}>
          <label>Commentaire</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={4}
            style={{ width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", gap: "1rem", marginTop: "1rem" }}>
          <button type="button" disabled={saving} onClick={save}>
            {saving ? "Enregistrement…" : "Enregistrer"}
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={remove}
            style={{ color: "#dc2626" }}
          >
            Supprimer la ligne
          </button>
        </div>

        {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}
      </div>
    </div>
  );
}

function messageFromError(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? "Échec de l'enregistrement.";
  }
  return "Échec de l'enregistrement.";
}
