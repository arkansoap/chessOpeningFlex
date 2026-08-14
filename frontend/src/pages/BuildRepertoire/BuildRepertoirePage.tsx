import { useState } from "react";
import ChessComImporter from "../../components/ChessComImporter/ChessComImporter";
import PgnUploader from "../../components/PgnUploader/PgnUploader";
import VariantAnalyzer from "../../components/VariantAnalyzer/VariantAnalyzer";
import LineSelector from "../../components/LineSelector/LineSelector";
import type { ImportedGame, VariantExtracted } from "../../types";

type Step = "import" | "analyze" | "select";

/**
 * Page 1: Build a repertoire.
 *
 * Step 1 — Import games (chess.com API or PGN upload).
 * Step 2 — Analyze the selected game and extract its variant(s).
 * Step 3 — Select the variant, trim depth, and save it to a repertoire.
 */
export default function BuildRepertoirePage() {
  const [step, setStep] = useState<Step>("import");
  const [games, setGames] = useState<ImportedGame[]>([]);
  const [selectedGameIdx, setSelectedGameIdx] = useState(0);
  const [selectedVariant, setSelectedVariant] = useState<VariantExtracted | null>(null);

  const handleImported = (imported: ImportedGame[]) => {
    setGames(imported);
    setSelectedGameIdx(0);
    setStep("analyze");
  };

  const selectedGame = games[selectedGameIdx];

  return (
    <div>
      <h1>Construire le répertoire</h1>

      {/* Stepper */}
      <ol style={{ display: "flex", gap: "1rem", listStyle: "none", padding: 0 }}>
        {(["import", "analyze", "select"] as Step[]).map((s, i) => (
          <li
            key={s}
            style={{
              fontWeight: step === s ? "bold" : "normal",
              opacity: stepIndex(step) >= i ? 1 : 0.4,
            }}
          >
            {i + 1}. {labelFor(s)}
          </li>
        ))}
      </ol>

      {step === "import" && (
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <section style={{ flex: 1, minWidth: 280 }}>
            <h2>Importer depuis chess.com</h2>
            <ChessComImporter onImported={handleImported} />
          </section>
          <section style={{ flex: 1, minWidth: 280 }}>
            <h2>Importer un fichier PGN</h2>
            <PgnUploader onImported={handleImported} />
          </section>
        </div>
      )}

      {step === "analyze" && games.length > 0 && (
        <div>
          <h2>Analyser les parties</h2>
          <label>
            Partie&nbsp;
            <select
              value={selectedGameIdx}
              onChange={(e) => setSelectedGameIdx(Number(e.target.value))}
            >
              {games.map((g, i) => (
                <option key={g.id ?? i} value={i}>
                  {g.white_player} vs {g.black_player} — {g.date ?? "?"}
                  {g.eco_code ? ` [${g.eco_code}]` : ""}
                </option>
              ))}
            </select>
          </label>

          <VariantAnalyzer
            pgn={selectedGame?.pgn_data}
            onSelectVariant={(v) => {
              setSelectedVariant(v);
              setStep("select");
            }}
          />

          <button type="button" onClick={() => setStep("import")}>
            ← Retour
          </button>
        </div>
      )}

      {step === "select" && (
        <div>
          <h2>Sélectionner et nettoyer la ligne</h2>
          {selectedVariant && (
            <VariantAnalyzer initialVariants={[selectedVariant]} />
          )}
          <LineSelector
            variant={selectedVariant}
            onAdded={() => {
              setSelectedVariant(null);
              setStep("import");
            }}
          />
          <button type="button" onClick={() => setStep("analyze")}>
            ← Retour
          </button>
        </div>
      )}

      {step === "analyze" && games.length === 0 && (
        <p>Aucune partie importée.</p>
      )}
    </div>
  );
}

function stepIndex(step: Step): number {
  return { import: 0, analyze: 1, select: 2 }[step];
}

function labelFor(step: Step): string {
  return { import: "Import", analyze: "Analyse", select: "Sélection" }[step];
}
