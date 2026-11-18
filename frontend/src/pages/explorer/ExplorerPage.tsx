import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { Square } from "chess.js";
import Board from "../../components/Board";
import GameRow from "../../components/GameRow";
import EngineAnalysis from "../../components/EngineAnalysis/EngineAnalysis";
import {
  ColorToggle,
  ErrorNote,
  FiltersBar,
  PageHeader,
  ResultBar,
  Tabs,
} from "../../components/common";
import { useAsync } from "../../hooks/useAsync";
import { useSettings } from "../../hooks/useSettings";
import { formatEval, lineToParam, paramToLine, positionOf, squaresOf } from "../../lib/chess";
import { plural } from "../../lib/format";
import { errorMessage, explorer as explorerApi, repertoire as repertoireApi } from "../../services/api";
import type { MoveRow } from "../../types";
import LichessPanel from "./LichessPanel";
import MovesTable from "./MovesTable";
import OpeningsSummary from "./OpeningsSummary";
import RepertoireBox from "./RepertoireBox";

type View = "arbre" | "bilan";
type Panel = "coups" | "parties" | "moteur" | "lichess";

/**
 * "Mes ouvertures": the tree of my games, one position at a time, and my
 * results by opening. The position lives in the URL (`?line=e4 e5 Nf3`) so
 * that other screens can link straight to it.
 */
export default function ExplorerPage() {
  const { color, filters } = useSettings();
  const [params, setParams] = useSearchParams();
  const lineParam = params.get("line") ?? "";
  const line = useMemo(() => paramToLine(lineParam), [lineParam]);
  const view: View = params.get("vue") === "bilan" ? "bilan" : "arbre";
  const [panel, setPanel] = useState<Panel>("coups");
  const [showFilters, setShowFilters] = useState(false);
  // Moves undone with "back", so that "forward" can replay them.
  const [future, setFuture] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // The board follows the URL at once; statistics arrive a moment later.
  const local = useMemo(() => positionOf(line), [line]);
  const position = useAsync(
    (signal) => explorerApi.position(color, filters, line, signal),
    [color, filters, lineParam]
  );
  // While the next position loads, the previous statistics stay on screen,
  // dimmed and inert, rather than collapsing the panel at every move.
  const data = position.data;
  const stale = position.loading;

  const goTo = useCallback(
    (next: string[], nextView: View = "arbre") => {
      const query: Record<string, string> = {};
      if (next.length > 0) query.line = lineToParam(next);
      if (nextView === "bilan") query.vue = "bilan";
      setParams(query, { replace: true });
      setActionError(null);
    },
    [setParams]
  );

  const play = useCallback(
    (san: string) => {
      setFuture((f) => (f[0] === san ? f.slice(1) : []));
      goTo([...line, san]);
    },
    [goTo, line]
  );
  const back = () => {
    if (line.length === 0) return;
    setFuture((f) => [line[line.length - 1], ...f]);
    goTo(line.slice(0, -1));
  };
  const forward = () => {
    // Replay what was undone, else follow my most frequent move.
    const next = future[0] ?? (stale ? undefined : data?.moves.find((m) => m.games > 0)?.san);
    if (next) play(next);
  };
  const jump = (length: number) => {
    setFuture(line.slice(length).concat(future));
    goTo(line.slice(0, length));
  };

  const choose = async (move: MoveRow) => {
    setSaving(true);
    setActionError(null);
    try {
      await repertoireApi.setMove(color, line, move.uci);
      position.reload();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const adoptLast = async () => {
    if (line.length === 0) return;
    setSaving(true);
    setActionError(null);
    try {
      await repertoireApi.setMove(color, line.slice(0, -1), line[line.length - 1]);
      position.reload();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const arrows = useMemo(() => {
    const out: [Square, Square, string][] = [];
    if (stale || !data?.my_turn) return out;
    const best = data.eval?.best_uci;
    const mine = data.repertoire?.move_uci;
    if (mine) out.push([...squaresOf(mine), "rgba(22, 163, 74, 0.75)"]);
    if (best && best !== mine) out.push([...squaresOf(best), "rgba(37, 99, 235, 0.6)"]);
    return out;
  }, [data, stale]);

  return (
    <div className="page">
      <PageHeader title="Mes ouvertures">
        <ColorToggle />
        <button
          type="button"
          className={`btn btn--ghost${showFilters ? " btn--active" : ""}`}
          aria-expanded={showFilters}
          onClick={() => setShowFilters((s) => !s)}
        >
          Filtres
          {filters.timeClasses.length + (filters.months ? 1 : 0) > 0 && (
            <span className="badge">{filters.timeClasses.length + (filters.months ? 1 : 0)}</span>
          )}
        </button>
      </PageHeader>
      {showFilters && <FiltersBar />}

      <Tabs<View>
        items={[
          { id: "arbre", label: "Arbre" },
          { id: "bilan", label: "Bilan par ouverture" },
        ]}
        value={view}
        onChange={(v) => goTo(line, v)}
      />

      {view === "bilan" ? (
        <OpeningsSummary
          onOpen={(openingLine) => {
            setFuture([]);
            goTo(openingLine);
          }}
        />
      ) : (
        <div className="explorer">
          <div className="explorer__board">
            <Board
              fen={local.fen}
              orientation={color}
              lastMove={local.lastMove}
              arrows={arrows}
              onMove={(move) => play(move.san)}
            />
            <div className="navrow">
              <button type="button" className="btn" onClick={() => jump(0)} disabled={line.length === 0} title="Position de départ">
                ⇤
              </button>
              <button type="button" className="btn" onClick={back} disabled={line.length === 0} title="Coup précédent">
                ◀
              </button>
              <button
                type="button"
                className="btn"
                onClick={forward}
                disabled={!future[0] && (stale || !data?.moves.some((m) => m.games > 0))}
                title="Coup suivant (le plus joué)"
              >
                ▶
              </button>
              <ol className="breadcrumb" aria-label="Coups joués">
                {line.length === 0 && <li className="muted">Position de départ</li>}
                {line.map((san, i) => (
                  <li key={i}>
                    {i % 2 === 0 && <span className="breadcrumb__number">{i / 2 + 1}.</span>}
                    <button
                      type="button"
                      className={`breadcrumb__move${i === line.length - 1 ? " breadcrumb__move--current" : ""}`}
                      onClick={() => jump(i + 1)}
                    >
                      {san}
                    </button>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          <div className={`explorer__panel${stale && data ? " explorer__panel--stale" : ""}`}>
            <ErrorNote message={position.error ?? actionError} />
            {data ? (
              <>
                <div className="summary">
                  <div className="summary__title">
                    {data.opening ? (
                      <>
                        {data.opening.name} <span className="muted">{data.opening.eco}</span>
                      </>
                    ) : (
                      "Position de départ"
                    )}
                  </div>
                  <div className="summary__stats">
                    <span>
                      <strong>{plural(data.games, "partie")}</strong>
                      {data.games > 0 && <> · score {Math.round(data.score)} %</>}
                    </span>
                    {data.eval && (
                      <span className="summary__eval" title="Évaluation Stockfish, côté blancs">
                        {formatEval(data.eval)}
                        {data.my_turn && data.eval.best_san && (
                          <span className="muted"> · meilleur {data.eval.best_san}</span>
                        )}
                      </span>
                    )}
                  </div>
                  {data.games > 0 && (
                    <ResultBar wins={data.wins} draws={data.draws} losses={data.losses} />
                  )}
                </div>

                <RepertoireBox
                  position={data}
                  onChanged={position.reload}
                  onAdoptLast={() => void adoptLast()}
                />

                <Tabs<Panel>
                  items={[
                    { id: "coups", label: data.my_turn ? "Mes coups" : "Coups adverses" },
                    { id: "parties", label: "Parties" },
                    { id: "moteur", label: "Moteur" },
                    { id: "lichess", label: "Lichess" },
                  ]}
                  value={panel}
                  onChange={setPanel}
                />
                {panel === "coups" && (
                  <MovesTable position={data} onPlay={play} onChoose={(m) => void choose(m)} busy={saving} />
                )}
                {panel === "parties" &&
                  (data.recent_games.length > 0 ? (
                    <ul className="games">
                      {data.recent_games.map((game) => (
                        <GameRow key={game.id} game={game} />
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">Aucune partie par cette position.</p>
                  ))}
                {panel === "moteur" && <EngineAnalysis fen={local.fen} multiPv={3} height={200} />}
                {panel === "lichess" && <LichessPanel line={line} onPlay={play} />}
              </>
            ) : (
              !position.error && <p className="muted">Chargement…</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
