import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorNote } from "../../components/common";
import { useSettings } from "../../hooks/useSettings";
import { explorerLink, numbered, numberedMove } from "../../lib/chess";
import { plural } from "../../lib/format";
import { errorMessage, repertoire as repertoireApi } from "../../services/api";
import type { Draft } from "../../types";

const REASONS = {
  hesitation: "pas de coup dominant",
  leak: "coup déconseillé par le moteur",
  not_analysed: "pas encore analysé",
} as const;

/** Draft from my games, and PGN import / export. */
export default function Tools({ onChanged }: { onChanged: () => void }) {
  const { color, filters } = useSettings();
  const [minGames, setMinGames] = useState(3);
  const [minShare, setMinShare] = useState(50);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [overwrite, setOverwrite] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const runDraft = async (dryRun: boolean) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await repertoireApi.draft(color, filters, {
        min_games: minGames,
        min_share: minShare / 100,
        max_loss: 5,
        dry_run: dryRun,
      });
      if (dryRun) {
        setDraft(result);
      } else {
        setDraft(null);
        setMessage(`${plural(result.added, "coup ajouté", "coups ajoutés")} au répertoire.`);
        onChanged();
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const importPgn = async (file: File) => {
    setError(null);
    setMessage(null);
    try {
      const counts = await repertoireApi.importPgn(color, await file.text(), overwrite);
      setMessage(
        `${plural(counts.added, "coup ajouté", "coups ajoutés")}, ` +
          `${counts.updated} remplacé(s), ${counts.kept} déjà présent(s).`
      );
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <>
      <ErrorNote message={error} />
      {message && <p className="note">{message}</p>}

      <section className="card">
        <h2>Brouillon à partir de mes parties</h2>
        <p className="muted">
          Part de la position de départ et suit mes parties : là où je joue presque toujours le même
          coup et que le moteur ne le déconseille pas, ce coup est proposé. Les coups déjà choisis
          ne sont jamais remplacés.
        </p>
        <div className="filters">
          <label className="filters__period">
            Position atteinte au moins
            <select value={minGames} onChange={(e) => setMinGames(Number(e.target.value))}>
              {[2, 3, 5, 10].map((n) => (
                <option key={n} value={n}>
                  {n} fois
                </option>
              ))}
            </select>
          </label>
          <label className="filters__period">
            Même coup dans au moins
            <select value={minShare} onChange={(e) => setMinShare(Number(e.target.value))}>
              {[50, 60, 75, 90].map((n) => (
                <option key={n} value={n}>
                  {n} % des cas
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="actions">
          <button type="button" className="btn btn--primary" disabled={busy} onClick={() => void runDraft(true)}>
            Voir la proposition
          </button>
        </div>

        {draft && (
          <div className="draft">
            <p>
              <strong>{plural(draft.additions.length, "coup proposé", "coups proposés")}</strong>
              {draft.skipped.length > 0 &&
                ` · ${plural(draft.skipped.length, "position laissée", "positions laissées")} de côté`}
            </p>
            {draft.additions.length > 0 && (
              <>
                <ul className="entries">
                  {draft.additions.map((item) => (
                    <li key={item.key} className="entries__row">
                      <Link to={explorerLink(item.line)} className="entries__line">
                        <span className="muted">{numbered(item.line)}</span>{" "}
                        <strong>{numberedMove(item.san, item.line.length)}</strong>
                      </Link>
                      <span className="muted">
                        {item.games} parties · {Math.round(item.share * 100)} %
                      </span>
                    </li>
                  ))}
                </ul>
                <div className="actions">
                  <button type="button" className="btn btn--primary" disabled={busy} onClick={() => void runDraft(false)}>
                    Ajouter ces {draft.additions.length} coups
                  </button>
                </div>
              </>
            )}
            {draft.skipped.length > 0 && (
              <details className="details">
                <summary>Positions laissées de côté ({draft.skipped.length})</summary>
                <ul className="entries">
                  {draft.skipped.map((item) => (
                    <li key={item.key} className="entries__row">
                      <Link to={explorerLink(item.line)} className="entries__line">
                        <span className="muted">{numbered(item.line) || "Départ"}</span>{" "}
                        <strong>{numberedMove(item.san, item.line.length)}</strong>
                      </Link>
                      <span className="muted">
                        {REASONS[item.reason]}
                        {item.reason === "leak" && item.best_san ? ` (plutôt ${item.best_san})` : ""}
                        {item.reason === "hesitation" && item.alternatives
                          ? ` (${item.alternatives.join(", ")})`
                          : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </section>

      <section className="card">
        <h2>PGN</h2>
        <p className="muted">
          L'export tient en une partie avec variantes : il s'ouvre dans une étude Lichess, ChessBase
          ou Chessable. À l'import, mes coups sont lus sur la ligne principale et les variantes.
        </p>
        <div className="actions">
          <a className="btn" href={repertoireApi.exportUrl(color)} download>
            Exporter le répertoire
          </a>
          <button type="button" className="btn" onClick={() => fileInput.current?.click()}>
            Importer un PGN…
          </button>
          <label className="check">
            <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
            Remplacer mes coups existants
          </label>
          <input
            ref={fileInput}
            type="file"
            accept=".pgn,.txt"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void importPgn(file);
              e.target.value = "";
            }}
          />
        </div>
      </section>
    </>
  );
}
