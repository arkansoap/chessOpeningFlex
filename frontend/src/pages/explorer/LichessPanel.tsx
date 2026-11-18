import { ResultBar } from "../../components/common";
import { useAsync } from "../../hooks/useAsync";
import { useSettings } from "../../hooks/useSettings";
import { percent } from "../../lib/format";
import { explorer as explorerApi } from "../../services/api";

/** What Lichess players around my level play in the position. */
export default function LichessPanel({
  line,
  onPlay,
}: {
  line: string[];
  onPlay: (san: string) => void;
}) {
  const { color, rating, setRating } = useSettings();
  const stats = useAsync(() => explorerApi.lichess(line, rating), [line.join(" "), rating]);

  return (
    <div>
      <label className="inline-field">
        Mon classement approximatif
        <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
          {[1000, 1200, 1400, 1500, 1600, 1800, 2000, 2200].map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </label>
      {stats.loading && !stats.data && <p className="muted">Chargement…</p>}
      {stats.error && <p className="error">{stats.error}</p>}
      {stats.data && !stats.data.available && (
        <p className="muted">
          Statistiques Lichess indisponibles : {stats.data.reason} Voir le README, section
          « Statistiques Lichess ».
        </p>
      )}
      {stats.data?.available && (
        <>
          <p className="muted">
            {stats.data.games.toLocaleString("fr-FR")} parties Lichess (classements{" "}
            {stats.data.ratings.replace(",", " et ")}).
          </p>
          <ul className="moves">
            {stats.data.moves.map((move) => {
              // Results from my side, whichever colour I play.
              const wins = color === "white" ? move.white : move.black;
              const losses = color === "white" ? move.black : move.white;
              return (
                <li key={move.uci} className="moves__row">
                  <button type="button" className="moves__play" onClick={() => onPlay(move.san)}>
                    <span className="moves__san">{move.san}</span>
                    <span className="moves__count">
                      {percent(move.games, stats.data?.available ? stats.data.games : 0)}
                    </span>
                    <span className="moves__bar">
                      <ResultBar wins={wins} draws={move.draws} losses={losses} />
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
