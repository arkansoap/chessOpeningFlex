import { useState } from "react";
import { EmptyState, ErrorNote, ResultBar } from "../../components/common";
import { useAsync } from "../../hooks/useAsync";
import { useSettings } from "../../hooks/useSettings";
import { paramToLine } from "../../lib/chess";
import { explorer as explorerApi } from "../../services/api";

/** My results opening by opening; a row opens the tree at that opening. */
export default function OpeningsSummary({ onOpen }: { onOpen: (line: string[]) => void }) {
  const { color, filters } = useSettings();
  const openings = useAsync(() => explorerApi.openings(color, filters), [color, filters]);
  const [expanded, setExpanded] = useState<string | null>(null);

  if (openings.error) return <ErrorNote message={openings.error} />;
  if (!openings.data) return <p className="muted">Chargement…</p>;
  if (openings.data.length === 0) {
    return (
      <EmptyState title="Aucune partie avec cette couleur">
        Synchronise tes parties depuis l'accueil, ou élargis les filtres.
      </EmptyState>
    );
  }
  const total = openings.data.reduce((sum, family) => sum + family.games, 0);

  return (
    <ul className="openings">
      {openings.data.map((family) => {
        const open = expanded === family.family;
        return (
          <li key={family.family} className="openings__family">
            <div className="openings__row">
              <button
                type="button"
                className="openings__name"
                onClick={() => onOpen(paramToLine(family.line))}
                title="Ouvrir dans l'arbre"
              >
                {family.family}
              </button>
              <span className="openings__games">
                {family.games}
                <span className="muted"> · {Math.round((100 * family.games) / total)} %</span>
              </span>
              <span className="openings__bar">
                <ResultBar wins={family.wins} draws={family.draws} losses={family.losses} />
              </span>
              <span className={`openings__score${family.score < 45 ? " openings__score--low" : ""}`}>
                {Math.round(family.score)} %
              </span>
              {family.variations.length > 1 ? (
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  aria-expanded={open}
                  title={`${family.variations.length} variantes`}
                  onClick={() => setExpanded(open ? null : family.family)}
                >
                  {open ? "▾" : `▸ ${family.variations.length}`}
                </button>
              ) : (
                <span />
              )}
            </div>
            {open && (
              <ul className="openings__variations">
                {family.variations.map((variation) => (
                  <li key={variation.name} className="openings__row openings__row--sub">
                    <button
                      type="button"
                      className="openings__name"
                      onClick={() => onOpen(paramToLine(variation.line))}
                    >
                      {variation.name.includes(":")
                        ? variation.name.split(":").slice(1).join(":").trim()
                        : variation.name}
                      {variation.eco && <span className="muted"> {variation.eco}</span>}
                    </button>
                    <span className="openings__games">{variation.games}</span>
                    <span className="openings__bar">
                      <ResultBar
                        wins={variation.wins}
                        draws={variation.draws}
                        losses={variation.losses}
                      />
                    </span>
                    <span className="openings__score">{Math.round(variation.score)} %</span>
                    <span />
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}
