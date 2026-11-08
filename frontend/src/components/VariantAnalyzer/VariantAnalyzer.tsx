import { useEffect, useState } from "react";
import { analysis } from "../../services/api";
import type { Color, VariantExtracted } from "../../types";
import VariantPlayer from "../ChessBoard/VariantPlayer";

export interface VariantAnalyzerProps {
  /** PGN to analyze. When provided, the analysis runs automatically. */
  pgn?: string;
  /**
   * Side the repertoire is being built for. The extracted line is truncated
   * so that it ends on this side's move.
   */
  color?: Color;
  /** Called when the user changes the side; omit to hide the control. */
  onColorChange?: (color: Color) => void;
  /** Variants to display directly (skip the API call). */
  initialVariants?: VariantExtracted[];
  /** Called when the user picks a variant to add to a repertoire. */
  onSelectVariant?: (variant: VariantExtracted) => void;
}

/**
 * Analyzes a PGN and displays the extracted variants, each previewable on a
 * chessboard. The user can select a variant to forward it to the repertoire
 * builder.
 */
export default function VariantAnalyzer({
  pgn,
  color = "white",
  onColorChange,
  initialVariants,
  onSelectVariant,
}: VariantAnalyzerProps) {
  const [variants, setVariants] = useState<VariantExtracted[]>(
    initialVariants ?? []
  );
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async (pgnText: string) => {
    if (!pgnText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analysis.variants(pgnText, color);
      setVariants(result);
      setSelectedIdx(0);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setLoading(false);
    }
  };

  // Re-run analysis whenever the PGN or the side changes (e.g. selecting
  // another game, or switching the repertoire colour, which changes where the
  // line is cut). Skipped when initialVariants were passed directly.
  useEffect(() => {
    if (initialVariants) return;
    if (pgn && pgn.trim()) {
      void runAnalysis(pgn);
    } else {
      setVariants([]);
    }
    // runAnalysis is stable enough for our purposes; we intentionally only
    // re-run when these change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pgn, color, initialVariants]);

  const selected = variants[selectedIdx];

  return (
    <div className="variant-analyzer">
      <h3>Variantes extraites</h3>

      {onColorChange && (
        <label>
          Répertoire pour les&nbsp;
          <select
            value={color}
            onChange={(e) => onColorChange(e.target.value as Color)}
          >
            <option value="white">blancs</option>
            <option value="black">noirs</option>
          </select>
          <span
            style={{ marginLeft: "0.6rem", color: "#6b7280", fontSize: "0.85rem" }}
          >
            la ligne extraite se termine sur un coup de cette couleur
          </span>
        </label>
      )}

      {loading && <p>Analyse en cours…</p>}
      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}

      {variants.length > 0 && (
        <div className="variant-analyzer__layout">
          {/* The variant list stays a narrow column so the board and the
              engine panel keep sitting side by side. */}
          <ul className="variant-list">
            {variants.map((v, i) => (
              <li
                key={i}
                className={`variant-list__item${
                  i === selectedIdx ? " variant-list__item--active" : ""
                }`}
                onClick={() => setSelectedIdx(i)}
              >
                {v.eco_code ? `[${v.eco_code}] ` : ""}
                {v.moves.split(" ").slice(0, 6).join(" ")}
                {v.moves.split(" ").length > 6 ? "…" : ""}
              </li>
            ))}
          </ul>

          <div className="variant-analyzer__board">
            <VariantPlayer
              moves={selected?.moves ?? ""}
              startingFen={selected?.starting_position}
            />
            {selected?.eco_code && <p>ECO : {selected.eco_code}</p>}
          </div>
        </div>
      )}

      {selected && onSelectVariant && (
        <button
          type="button"
          onClick={() => onSelectVariant(selected)}
          style={{ marginTop: "1rem" }}
        >
          Sélectionner cette variante →
        </button>
      )}
    </div>
  );
}

function messageFromError(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? "Échec de l'analyse.";
  }
  return "Échec de l'analyse.";
}
