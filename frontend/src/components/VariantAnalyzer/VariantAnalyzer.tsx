import { useState } from "react";
import { analysis } from "../../services/api";
import type { VariantExtracted } from "../../types";
import VariantPlayer from "../ChessBoard/VariantPlayer";

export interface VariantAnalyzerProps {
  /** PGN to analyze. When provided, the analysis runs automatically. */
  pgn?: string;
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
      const result = await analysis.variants(pgnText);
      setVariants(result);
      setSelectedIdx(0);
    } catch (e: unknown) {
      setError(messageFromError(e));
    } finally {
      setLoading(false);
    }
  };

  // Auto-run analysis when a new PGN is provided.
  if (pgn && variants.length === 0 && !loading && !error) {
    void runAnalysis(pgn);
  }

  const selected = variants[selectedIdx];

  return (
    <div className="variant-analyzer">
      <h3>Variantes extraites</h3>
      {loading && <p>Analyse en cours…</p>}
      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}

      {variants.length > 0 && (
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <div>
            <VariantPlayer
              moves={selected?.moves ?? ""}
              startingFen={selected?.starting_position}
            />
            {selected?.eco_code && (
              <p>ECO : {selected.eco_code}</p>
            )}
          </div>

          <ul style={{ listStyle: "none", padding: 0 }}>
            {variants.map((v, i) => (
              <li
                key={i}
                style={{
                  cursor: "pointer",
                  padding: "0.5rem",
                  background: i === selectedIdx ? "#dbeafe" : "transparent",
                  borderRadius: 4,
                }}
                onClick={() => setSelectedIdx(i)}
              >
                {v.eco_code ? `[${v.eco_code}] ` : ""}
                {v.moves.split(" ").slice(0, 6).join(" ")}
                {v.moves.split(" ").length > 6 ? "…" : ""}
              </li>
            ))}
          </ul>
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
