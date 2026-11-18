import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyState, ErrorNote } from "../../components/common";
import { explorerLink, numbered, numberedMove } from "../../lib/chess";
import { errorMessage, repertoire as repertoireApi } from "../../services/api";
import type { RepertoireData, RepertoireEntry } from "../../types";

export const LEVEL_LABELS = ["à apprendre", "4 h", "1 j", "3 j", "1 sem.", "2 sem.", "1 mois", "3 mois", "6 mois"];

/** Every move of the repertoire, grouped by opening. */
export default function EntriesList({
  data,
  onChanged,
}: {
  data: RepertoireData | null;
  onChanged: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const groups = useMemo(() => {
    const byOpening = new Map<string, RepertoireEntry[]>();
    for (const entry of data?.items ?? []) {
      const family = (entry.opening ?? "Sans nom").split(":")[0].trim();
      byOpening.set(family, [...(byOpening.get(family) ?? []), entry]);
    }
    return [...byOpening.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [data]);

  if (!data) return <p className="muted">Chargement…</p>;
  if (data.items.length === 0) {
    return (
      <EmptyState title="Le répertoire est vide">
        Va dans l'onglet Outils pour tirer un brouillon de tes parties, ou choisis tes coups un à un
        dans Mes ouvertures avec l'étoile ☆.
      </EmptyState>
    );
  }

  const remove = async (entry: RepertoireEntry) => {
    setError(null);
    try {
      await repertoireApi.remove(entry.id);
      onChanged();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <>
      <ErrorNote message={error} />
      {groups.map(([family, entries]) => (
        <details key={family} className="group" open={groups.length <= 4}>
          <summary>
            {family} <span className="badge">{entries.length}</span>
          </summary>
          <ul className="entries">
            {entries.map((entry) => (
              <li key={entry.id} className="entries__row">
                <Link to={explorerLink(entry.line)} className="entries__line">
                  <span className="muted">{numbered(entry.line)}</span>{" "}
                  <strong>{numberedMove(entry.move_san, entry.line.length)}</strong>
                  {entry.comment && <span className="entries__note"> — {entry.comment}</span>}
                </Link>
                <span className={`level level--${Math.min(entry.srs_level, 8)}`}>
                  {LEVEL_LABELS[Math.min(entry.srs_level, 8)]}
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--small"
                  title="Retirer du répertoire"
                  onClick={() => void remove(entry)}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </details>
      ))}
    </>
  );
}
