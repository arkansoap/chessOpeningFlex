import { useState } from "react";
import { Link } from "react-router-dom";
import MiniBoard from "../../components/MiniBoard";
import { EmptyState, ErrorNote } from "../../components/common";
import { useSettings } from "../../hooks/useSettings";
import { explorerLink, numbered } from "../../lib/chess";
import { formatDate, plural } from "../../lib/format";
import { errorMessage, repertoire as repertoireApi } from "../../services/api";
import type { Coverage, Gap } from "../../types";

/**
 * Positions where my games leave the repertoire because I have not chosen a
 * move there, most frequent first: the next ones to prepare.
 */
export default function GapsList({
  coverage,
  onChanged,
}: {
  coverage: Coverage | null;
  onChanged: () => void;
}) {
  const { color } = useSettings();
  const [error, setError] = useState<string | null>(null);
  const [shown, setShown] = useState(20);

  if (!coverage) return <p className="muted">Chargement…</p>;
  if (coverage.games === 0) {
    return (
      <EmptyState title="Aucune partie avec cette couleur">
        Synchronise tes parties depuis l'accueil.
      </EmptyState>
    );
  }
  if (coverage.gaps.length === 0) {
    return (
      <EmptyState title="Aucun trou">
        Dans toutes mes parties, le répertoire a une réponse jusqu'à la fin de l'ouverture indexée.
      </EmptyState>
    );
  }

  const choose = async (gap: Gap, san: string) => {
    setError(null);
    try {
      await repertoireApi.setMove(color, gap.line, san);
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <>
      <p className="muted">
        {plural(coverage.with_gap, "partie")} sur {coverage.games}{" "}
        {coverage.with_gap > 1 ? "sortent" : "sort"} du répertoire faute de coup choisi. Le plus
        fréquent d'abord : choisir un coup ici, c'est couvrir le plus de parties d'un coup.
      </p>
      <ErrorNote message={error} />
      <ul className="cards">
        {coverage.gaps.slice(0, shown).map((gap) => (
          <li key={gap.key} className="card leak">
            <Link to={explorerLink(gap.line)} className="leak__board" title="Ouvrir dans l'arbre">
              <MiniBoard line={gap.line} orientation={color} />
            </Link>
            <div className="leak__intro">
              <div className="leak__head">
                <strong>{plural(gap.games, "partie")}</strong>
              </div>
              <div className="muted">{gap.opening ?? ""}</div>
              <p className="leak__line">{numbered(gap.line) || "Position de départ"}</p>
            </div>
            <div className="leak__body">
              <p className="muted">
                J'y ai joué : {gap.played.map((p) => `${p.san} (${p.games})`).join(", ")}
                {gap.last_played ? ` · dernière fois ${formatDate(gap.last_played)}` : ""}
              </p>
              <div className="actions">
                {gap.played.slice(0, 3).map((p) => (
                  <button key={p.san} type="button" className="btn" onClick={() => void choose(gap, p.san)}>
                    ★ {p.san}
                  </button>
                ))}
                <Link className="btn btn--ghost" to={explorerLink(gap.line)}>
                  Voir les évaluations
                </Link>
              </div>
            </div>
          </li>
        ))}
      </ul>
      {coverage.gaps.length > shown && (
        <button type="button" className="btn" onClick={() => setShown(shown + 20)}>
          Afficher la suite ({coverage.gaps.length - shown})
        </button>
      )}
    </>
  );
}
