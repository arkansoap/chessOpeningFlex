import { Link } from "react-router-dom";
import GameRow from "../../components/GameRow";
import { EmptyState, ErrorNote } from "../../components/common";
import { useAsync } from "../../hooks/useAsync";
import { useSettings } from "../../hooks/useSettings";
import { explorerLink, numberedMove } from "../../lib/chess";
import { plural } from "../../lib/format";
import { repertoire as repertoireApi } from "../../services/api";

/** My latest games, each with the point where it left the repertoire. */
export default function ReviewList() {
  const { color } = useSettings();
  const review = useAsync(() => repertoireApi.review(color, 40), [color]);

  if (review.error) return <ErrorNote message={review.error} />;
  if (!review.data) return <p className="muted">Chargement…</p>;
  if (review.data.length === 0) {
    return <EmptyState title="Aucune partie avec cette couleur" />;
  }
  return (
    <ul className="games">
      {review.data.map((item) => (
        <GameRow key={item.game.id} game={item.game}>
          {item.status === "covered" && (
            <span className="tag tag--ok">
              Dans le répertoire sur toute l'ouverture ({plural(item.followed, "coup")})
            </span>
          )}
          {item.status === "deviation" && (
            <>
              <span className="tag tag--mistake">Écart</span>{" "}
              J'ai joué <strong>{numberedMove(item.played ?? "", item.ply)}</strong> au lieu de{" "}
              <strong>{item.expected}</strong>.{" "}
              <Link to={explorerLink(item.line)}>Voir la position</Link>
            </>
          )}
          {item.status === "gap" && (
            <>
              <span className="tag tag--todo">Hors répertoire</span>{" "}
              {item.line.length > 0 ? (
                <>
                  Après <strong>{numberedMove(item.line[item.line.length - 1], item.ply - 1)}</strong>,
                  aucun coup choisi
                </>
              ) : (
                "Aucun premier coup choisi"
              )}{" "}
              (j'ai joué {item.played}). <Link to={explorerLink(item.line)}>Choisir mon coup</Link>
            </>
          )}
          {item.game.opening_name && <div className="muted">{item.game.opening_name}</div>}
        </GameRow>
      ))}
    </ul>
  );
}
