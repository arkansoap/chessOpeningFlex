import { useEffect, useState } from "react";
import { repertoire as repertoireApi } from "../../services/api";
import RepertoireSelect from "../RepertoireSelect/RepertoireSelect";
import type { Color, Repertoire, VariantExtracted } from "../../types";

export interface LineSelectorProps {
  variant: VariantExtracted | null;
  /** Side the line was extracted for; used to keep the target coherent. */
  color?: Color;
  /** Called after the line is successfully added to a repertoire. */
  onAdded?: (lineId: string) => void;
}

/**
 * Lets the user pick a target repertoire and trim the variant to a chosen
 * depth (number of plies), then persist it as a repertoire line.
 */
export default function LineSelector({
  variant,
  color = "white",
  onAdded,
}: LineSelectorProps) {
  const [repertoireId, setRepertoireId] = useState("");
  const [target, setTarget] = useState<Repertoire | undefined>();
  const [maxDepth, setMaxDepth] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

      <RepertoireSelect
        label="Répertoire cible"
        value={repertoireId}
        preferredColor={color}
        onChange={(id, repertoire) => {
          setRepertoireId(id);
          setTarget(repertoire);
          setError(null);
        }}
      />

      {/* The line was cut to end on `color`'s move, so filing it under the
          other side would store a line that never reaches the user's turn. */}
      {target && target.color !== color && (
        <p style={{ color: "#b45309" }}>
          ⚠ La ligne a été extraite pour les{" "}
          {color === "white" ? "blancs" : "noirs"}, mais «&nbsp;{target.name}
          &nbsp;» est un répertoire pour les{" "}
          {target.color === "white" ? "blancs" : "noirs"}.
        </p>
      )}

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
