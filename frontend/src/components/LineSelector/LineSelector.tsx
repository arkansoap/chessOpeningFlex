import { useEffect, useState } from "react";
import { repertoire as repertoireApi } from "../../services/api";
import type { Repertoire, VariantExtracted } from "../../types";

export interface LineSelectorProps {
  variant: VariantExtracted | null;
  /** Called after the line is successfully added to a repertoire. */
  onAdded?: (lineId: string) => void;
}

/**
 * Lets the user pick a target repertoire and trim the variant to a chosen
 * depth (number of plies), then persist it as a repertoire line.
 */
export default function LineSelector({ variant, onAdded }: LineSelectorProps) {
  const [repertoires, setRepertoires] = useState<Repertoire[]>([]);
  const [repertoireId, setRepertoireId] = useState("");
  const [maxDepth, setMaxDepth] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void repertoireApi.list().then(setRepertoires).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (variant) {
      const plies = variant.moves.split(" ").filter(Boolean).length;
      setMaxDepth(plies);
    }
  }, [variant]);

  if (!variant) {
    return <p>Sélectionnez d'abord une variante à intégrer.</p>;
  }

  const plies = variant.moves.split(" ").filter(Boolean);
  const trimmed = plies.slice(0, maxDepth).join(" ");

  const add = async () => {
    if (!repertoireId) {
      setError("Veuillez choisir un répertoire cible.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const line = await repertoireApi.addLine({
        repertoire_id: repertoireId,
        moves: trimmed,
        starting_position: variant.starting_position,
        depth: maxDepth,
      });
      onAdded?.(line.id);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="line-selector">
      <h3>Intégrer la ligne</h3>
      <p style={{ fontFamily: "monospace" }}>{trimmed || "—"}</p>

      <label>
        Répertoire cible&nbsp;
        <select
          value={repertoireId}
          onChange={(e) => setRepertoireId(e.target.value)}
        >
          <option value="">— Choisir —</option>
          {repertoires.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name} ({r.color})
            </option>
          ))}
        </select>
      </label>

      <label>
        Profondeur (coups)&nbsp;
        <input
          type="range"
          min={1}
          max={plies.length}
          value={maxDepth}
          onChange={(e) => setMaxDepth(Number(e.target.value))}
        />
        <span>{maxDepth}</span>
      </label>

      <button type="button" disabled={loading} onClick={add}>
        {loading ? "Enregistrement…" : "Enregistrer la ligne"}
      </button>
      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}
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
