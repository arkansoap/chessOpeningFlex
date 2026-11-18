import { useState } from "react";
import { Link } from "react-router-dom";
import MiniBoard from "../components/MiniBoard";
import {
  ColorToggle,
  EmptyState,
  ErrorNote,
  FiltersBar,
  PageHeader,
  ResultBar,
} from "../components/common";
import { useAsync } from "../hooks/useAsync";
import { useSettings } from "../hooks/useSettings";
import { explorerLink, numbered, numberedMove, squaresOf } from "../lib/chess";
import { formatDate, plural } from "../lib/format";
import { analysis as analysisApi, errorMessage, repertoire as repertoireApi } from "../services/api";
import type { Leak } from "../types";
import { severityClass } from "./explorer/MovesTable";

const THRESHOLDS = [
  { value: 5, label: "Imprécisions et plus" },
  { value: 10, label: "Erreurs et gaffes" },
  { value: 15, label: "Gaffes seulement" },
];

/**
 * "Mes fuites": the moves I keep playing although the engine rates them
 * clearly below its best move, most costly first.
 */
export default function LeaksPage() {
  const { color, filters } = useSettings();
  const [minLoss, setMinLoss] = useState(5);
  const [minGames, setMinGames] = useState(2);
  const [hideFixed, setHideFixed] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = useAsync(() => analysisApi.status(), []);
  const leaks = useAsync(
    () => analysisApi.leaks(color, filters, minLoss, minGames),
    [color, filters, minLoss, minGames]
  );

  const adopt = async (leak: Leak) => {
    setError(null);
    try {
      await repertoireApi.setMove(color, leak.line, leak.best_uci, "leak");
      leaks.reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const items = (leaks.data?.leaks ?? []).filter(
    (leak) => !hideFixed || leak.repertoire_move !== leak.best_san
  );

  return (
    <div className="page">
      <PageHeader title="Mes fuites">
        <ColorToggle />
        <button
          type="button"
          className={`btn btn--ghost${showFilters ? " btn--active" : ""}`}
          aria-expanded={showFilters}
          onClick={() => setShowFilters((s) => !s)}
        >
          Filtres
        </button>
      </PageHeader>
      {showFilters && <FiltersBar />}
      <div className="filters" hidden={!showFilters}>
        <label className="filters__period">
          Gravité
          <select value={minLoss} onChange={(e) => setMinLoss(Number(e.target.value))}>
            {THRESHOLDS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label className="filters__period">
          Joué au moins
          <select value={minGames} onChange={(e) => setMinGames(Number(e.target.value))}>
            {[2, 3, 5, 10].map((n) => (
              <option key={n} value={n}>
                {n} fois
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={hideFixed} onChange={(e) => setHideFixed(e.target.checked)} />
          Masquer celles déjà corrigées au répertoire
        </label>
      </div>

      <ErrorNote message={error ?? leaks.error} />
      {status.data && status.data.pending > 0 && (
        <p className="note">
          {plural(status.data.pending, "position")} de mes parties{" "}
          {status.data.pending > 1 ? "ne sont pas encore analysées" : "n'est pas encore analysée"} :
          lance l'analyse depuis l'<Link to="/">accueil</Link> pour une liste complète.
        </p>
      )}

      {leaks.data && items.length === 0 && (
        <EmptyState title="Aucune fuite à ce niveau de gravité">
          {status.data && status.data.total === 0
            ? "Importe d'abord tes parties depuis l'accueil."
            : "Soit tes coups répétés tiennent la route, soit l'analyse n'a pas encore tourné."}
        </EmptyState>
      )}

      <ul className="cards">
        {items.map((leak) => {
          const fixed = leak.repertoire_move === leak.best_san;
          const ply = leak.line.length;
          return (
            <li key={`${leak.key}-${leak.move.uci}`} className="card leak">
              <Link to={explorerLink(leak.line)} className="leak__board" title="Ouvrir dans l'arbre">
                <MiniBoard
                  line={leak.line}
                  orientation={color}
                  highlight={[...squaresOf(leak.move.uci), ...squaresOf(leak.best_uci)]}
                />
              </Link>
              <div className="leak__intro">
                <div className="leak__head">
                  <span className={`tag tag--${severityClass(leak.severity)}`}>{leak.severity}</span>
                  <strong>
                    {numberedMove(leak.move.san, ply)} → {leak.best_san}
                  </strong>
                </div>
                <div className="muted">{leak.opening ?? "Ouverture sans nom"}</div>
                <p className="leak__line">{numbered(leak.line) || "Position de départ"}</p>
              </div>
              <div className="leak__body">
                <p>
                  Je joue <strong>{numberedMove(leak.move.san, ply)}</strong> —{" "}
                  {plural(leak.move.games, "partie")} sur {leak.position_games}, score{" "}
                  {Math.round(leak.move.score)} %.
                  <br />
                  Stockfish préfère <strong>{numberedMove(leak.best_san, ply)}</strong> :{" "}
                  {leak.loss_cp !== null
                    ? `mon coup perd ${(leak.loss_cp / 100).toFixed(1).replace(".", ",")} pion`
                    : "mon coup laisse passer un mat"}{" "}
                  <span className="muted">(−{Math.round(leak.loss)} points d'espérance de gain)</span>.
                </p>
                <div className="leak__bar">
                  <ResultBar wins={leak.move.wins} draws={leak.move.draws} losses={leak.move.losses} />
                </div>
                {leak.pv_san && <p className="muted leak__pv">Suite : {leak.pv_san}</p>}
                <div className="actions">
                  {fixed ? (
                    <span className="tag tag--ok">
                      ★ {leak.best_san} est mon coup de répertoire — à ancrer à l'entraînement
                    </span>
                  ) : (
                    <button type="button" className="btn btn--primary" onClick={() => void adopt(leak)}>
                      ★ Mettre {leak.best_san} dans mon répertoire
                    </button>
                  )}
                  <Link className="btn btn--ghost" to={explorerLink(leak.line)}>
                    Voir la position
                  </Link>
                  {leak.move.last_played && (
                    <span className="muted">Dernière fois : {formatDate(leak.move.last_played)}</span>
                  )}
                </div>
                {leak.repertoire_move && !fixed && (
                  <p className="muted">Au répertoire actuellement : {leak.repertoire_move}.</p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
