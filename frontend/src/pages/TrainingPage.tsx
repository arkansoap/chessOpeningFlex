import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Chess, type Square } from "chess.js";
import Board, { type PlayedMove } from "../components/Board";
import { EmptyState, ErrorNote, PageHeader } from "../components/common";
import { useAsync } from "../hooks/useAsync";
import { explorerLink, numbered, numberedMove, positionOf, squaresOf } from "../lib/chess";
import { plural } from "../lib/format";
import { errorMessage, training as trainingApi } from "../services/api";
import type { Color, Question, RepertoireEntry } from "../types";
import { LEVEL_LABELS } from "./repertoire/EntriesList";

type Scope = Color | "any";
type Phase = "asking" | "correct" | "wrong";

const SCOPE_KEY = "chessopeningflex.training.scope";

/**
 * Training: the position appears, I play my repertoire move. A right answer
 * pushes the next review further away, a wrong one brings the move back soon.
 */
export default function TrainingPage() {
  const [scope, setScope] = useState<Scope>(
    () => (localStorage.getItem(SCOPE_KEY) as Scope | null) ?? "any"
  );
  const [mode, setMode] = useState<"due" | "all">("due");
  const [question, setQuestion] = useState<Question | null>(null);
  const [remaining, setRemaining] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const [phase, setPhase] = useState<Phase>("asking");
  const [entry, setEntry] = useState<RepertoireEntry | null>(null);
  const [wrongMove, setWrongMove] = useState<PlayedMove | null>(null);
  const [session, setSession] = useState({ asked: 0, correct: 0 });
  const [error, setError] = useState<string | null>(null);
  const stats = useAsync(() => trainingApi.stats(), [session.asked]);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const loadNext = useCallback(
    async (exclude?: string) => {
      clearTimeout(timer.current);
      try {
        const next = await trainingApi.next(scope, mode, exclude);
        setQuestion(next.question);
        setRemaining(next.remaining);
        setPhase("asking");
        setEntry(null);
        setWrongMove(null);
        setError(null);
      } catch (e) {
        setError(errorMessage(e));
      } finally {
        setLoaded(true);
      }
    },
    [scope, mode]
  );

  useEffect(() => {
    try {
      localStorage.setItem(SCOPE_KEY, scope);
    } catch {
      // Not remembered, nothing more.
    }
    void loadNext();
    return () => clearTimeout(timer.current);
  }, [loadNext, scope]);

  const context = useMemo(() => (question ? positionOf(question.line) : null), [question]);

  const submit = async (move: PlayedMove | null) => {
    if (!question) return;
    try {
      const result = await trainingApi.answer(question.entry_id, move?.uci ?? "", move === null);
      setEntry(result.entry);
      setSession((s) => ({ asked: s.asked + 1, correct: s.correct + (result.correct ? 1 : 0) }));
      if (result.correct) {
        setPhase("correct");
        timer.current = setTimeout(() => void loadNext(question.entry_id), result.entry.comment ? 2600 : 1100);
      } else {
        setPhase("wrong");
        setWrongMove(move);
      }
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  const handleMove = (move: PlayedMove) => {
    if (!question) return;
    if (phase === "asking") {
      void submit(move);
    } else if (phase === "wrong" && entry) {
      // The answer is shown: playing it moves on, anything else flashes again.
      if (move.uci === entry.move_uci) void loadNext(question.entry_id);
      else setWrongMove(move);
    }
  };

  // After a right answer the board shows the move played.
  const shownFen = useMemo(() => {
    if (!question) return null;
    if (phase !== "correct" || !entry) return question.fen;
    const game = new Chess(question.fen);
    try {
      game.move(entry.move_san);
    } catch {
      return question.fen;
    }
    return game.fen();
  }, [question, phase, entry]);

  const expected = entry ? squaresOf(entry.move_uci) : null;
  const squareColors: Record<string, string> = {};
  if (phase === "wrong" && wrongMove) {
    squareColors[wrongMove.from] = "var(--flash-wrong)";
    squareColors[wrongMove.to] = "var(--flash-wrong)";
  }
  const lastMove: { from: Square; to: Square } | null =
    phase === "correct" && expected
      ? { from: expected[0], to: expected[1] }
      : (context?.lastMove ?? null);

  const totals = stats.data?.colors;
  return (
    <div className="page">
      <PageHeader title="Entraînement">
        <div className="segmented" role="group" aria-label="Répertoire à réviser">
          {(["any", "white", "black"] as const).map((s) => (
            <button
              key={s}
              type="button"
              className={`segmented__item${scope === s ? " segmented__item--active" : ""}`}
              aria-pressed={scope === s}
              onClick={() => setScope(s)}
            >
              {s === "any" ? "Tout" : s === "white" ? "Blancs" : "Noirs"}
            </button>
          ))}
        </div>
      </PageHeader>
      <ErrorNote message={error} />

      {loaded && !question && (
        <EmptyState
          title={
            totals && totals.white.entries + totals.black.entries === 0
              ? "Le répertoire est vide"
              : "Rien à réviser pour l'instant"
          }
        >
          {totals && totals.white.entries + totals.black.entries === 0 ? (
            <>
              Commence par choisir des coups dans <Link to="/repertoire?vue=outils">Répertoire › Outils</Link>.
            </>
          ) : (
            <>
              Les prochaines révisions arriveront d'elles-mêmes.{" "}
              {mode === "due" && (
                <button type="button" className="btn" onClick={() => setMode("all")}>
                  Réviser quand même
                </button>
              )}
            </>
          )}
        </EmptyState>
      )}

      {question && shownFen && (
        <div className="explorer">
          <div className="explorer__board">
            <Board
              fen={shownFen}
              orientation={question.color}
              lastMove={lastMove}
              arrows={
                phase === "wrong" && expected
                  ? [[expected[0], expected[1], "rgba(22, 163, 74, 0.8)"]]
                  : []
              }
              squareColors={squareColors}
              onMove={phase === "correct" ? undefined : handleMove}
            />
          </div>
          <div className="explorer__panel">
            <div className={`quiz quiz--${phase}`} role="status">
              {phase === "asking" && (
                <>
                  <strong>
                    À moi de jouer avec les {question.color === "white" ? "blancs" : "noirs"}
                  </strong>
                  <span className="muted">
                    {question.is_new ? "Nouveau coup" : `Niveau ${LEVEL_LABELS[question.srs_level]}`}
                  </span>
                </>
              )}
              {phase === "correct" && entry && (
                <>
                  <strong>✓ {numberedMove(entry.move_san, question.line.length)}</strong>
                  <span className="muted">Prochaine révision dans {LEVEL_LABELS[entry.srs_level]}</span>
                </>
              )}
              {phase === "wrong" && entry && (
                <>
                  <strong>
                    ✗ Mon coup est {numberedMove(entry.move_san, question.line.length)}
                  </strong>
                  <span className="muted">Joue-le sur l'échiquier pour continuer.</span>
                </>
              )}
            </div>
            {entry?.comment && phase !== "asking" && <p className="quiz__note">{entry.comment}</p>}
            <p className="leak__line">{numbered(question.line) || "Position de départ"}</p>

            <div className="actions">
              {phase === "asking" && (
                <button type="button" className="btn" onClick={() => void submit(null)}>
                  Voir la réponse
                </button>
              )}
              {phase !== "asking" && (
                <button type="button" className="btn btn--primary" onClick={() => void loadNext(question.entry_id)}>
                  Suivant
                </button>
              )}
              <Link className="btn btn--ghost" to={explorerLink(question.line)}>
                Voir la position
              </Link>
            </div>
            <p className="muted">
              {mode === "due" ? `${plural(remaining, "coup")} dans la file` : "Révision libre de tout le répertoire"}
              {session.asked > 0 && ` · cette séance : ${session.correct} / ${session.asked}`}
              {mode === "all" && (
                <>
                  {" · "}
                  <button type="button" className="linklike" onClick={() => setMode("due")}>
                    revenir aux révisions dues
                  </button>
                </>
              )}
            </p>
          </div>
        </div>
      )}

      {stats.data && (
        <section className="card">
          <h2>Progression</h2>
          <div className="tiles">
            {(["white", "black"] as const).map((c) => (
              <div className="tile" key={c}>
                <span className="tile__value">
                  {stats.data!.colors[c].learned}
                  <span className="muted"> / {stats.data!.colors[c].entries}</span>
                </span>
                <span className="tile__label">
                  {c === "white" ? "Blancs" : "Noirs"} : coups ancrés (1 semaine ou plus) ·{" "}
                  {stats.data!.colors[c].new} à apprendre · {stats.data!.colors[c].due} à revoir
                </span>
              </div>
            ))}
          </div>
          <ActivityChart days={stats.data.days} />
        </section>
      )}
    </div>
  );
}

/** Answers per day over the last two weeks, right ones in green. */
function ActivityChart({ days }: { days: { date: string; reviews: number; correct: number }[] }) {
  const recent = useMemo(() => {
    const byDate = new Map(days.map((d) => [d.date, d]));
    const out = [];
    for (let i = 13; i >= 0; i--) {
      const date = new Date();
      date.setUTCDate(date.getUTCDate() - i);
      const key = date.toISOString().slice(0, 10);
      out.push(byDate.get(key) ?? { date: key, reviews: 0, correct: 0 });
    }
    return out;
  }, [days]);
  const max = Math.max(1, ...recent.map((d) => d.reviews));
  if (recent.every((d) => d.reviews === 0)) return null;
  return (
    <div className="activity" role="img" aria-label="Réponses par jour sur 14 jours">
      {recent.map((day) => (
        <div
          key={day.date}
          className="activity__day"
          title={`${day.date} : ${day.correct} justes sur ${day.reviews}`}
        >
          <div className="activity__bar" style={{ height: `${(100 * day.reviews) / max}%` }}>
            <div
              className="activity__correct"
              style={{ height: day.reviews ? `${(100 * day.correct) / day.reviews}%` : 0 }}
            />
          </div>
          <span className="activity__label">{day.date.slice(8)}</span>
        </div>
      ))}
    </div>
  );
}
