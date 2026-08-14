import { useEffect, useState } from "react";
import TrainingMode from "../../components/TrainingMode/TrainingMode";
import StatsDashboard from "../../components/StatsDashboard/StatsDashboard";
import { repertoire as repertoireApi } from "../../services/api";
import { training as trainingApi } from "../../services/api";
import type { Repertoire, RepertoireDetail } from "../../types";

type Mode = "random" | "sequential" | "full_variation";

const MODES: { value: Mode; label: string }[] = [
  { value: "random", label: "Aléatoire" },
  { value: "sequential", label: "Enchaîné" },
  { value: "full_variation", label: "Variante complète" },
];

/**
 * Page 3: Training.
 *
 * Select a repertoire + line + mode, then answer questions. A completed set of
 * answers is recorded as a session and feeds the statistics dashboard.
 */
export default function TrainingPage() {
  const [repertoires, setRepertoires] = useState<Repertoire[]>([]);
  const [repId, setRepId] = useState("");
  const [detail, setDetail] = useState<RepertoireDetail | null>(null);
  const [lineId, setLineId] = useState("");
  const [mode, setMode] = useState<Mode>("random");
  const [step, setStep] = useState(0);
  const [session, setSession] = useState({ correct: 0, total: 0 });

  useEffect(() => {
    void repertoireApi.list().then((reps) => {
      setRepertoires(reps);
      if (reps.length > 0) setRepId(reps[0].id);
    });
  }, []);

  useEffect(() => {
    if (!repId) return;
    void repertoireApi
      .get(repId)
      .then((d) => {
        setDetail(d);
        if (d.lines.length > 0) setLineId(d.lines[0].id);
      })
      .catch(() => setDetail(null));
  }, [repId]);

  const line = detail?.lines.find((l) => l.id === lineId) ?? null;

  const handleAnswer = (correct: boolean) => {
    setSession((prev) => ({
      correct: prev.correct + (correct ? 1 : 0),
      total: prev.total + 1,
    }));
    if (correct) setStep((s) => s + 1);
  };

  const finishSession = async () => {
    if (!line || session.total === 0) return;
    try {
      await trainingApi.recordSession({
        repertoire_id: repId,
        line_id: line.id,
        mode,
        total_questions: session.total,
        correct_answers: session.correct,
      });
      setSession({ correct: 0, total: 0 });
      setStep(0);
    } catch {
      // surfaced nowhere for now; the dashboard will simply not update
    }
  };

  return (
    <div>
      <h1>Entraînement</h1>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <label>
          Répertoire&nbsp;
          <select value={repId} onChange={(e) => setRepId(e.target.value)}>
            {repertoires.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.color})
              </option>
            ))}
          </select>
        </label>

        <label>
          Ligne&nbsp;
          <select value={lineId} onChange={(e) => setLineId(e.target.value)}>
            {(detail?.lines ?? []).map((l) => (
              <option key={l.id} value={l.id}>
                {l.moves.split(" ").slice(0, 4).join(" ")}
                {l.moves.split(" ").length > 4 ? "…" : ""}
              </option>
            ))}
          </select>
        </label>

        <label>
          Mode&nbsp;
          <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
            {MODES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {line ? (
        <TrainingMode
          key={`${line.id}-${mode}`}
          line={line}
          mode={mode}
          step={step}
          onAnswer={handleAnswer}
        />
      ) : (
        <p>Sélectionnez une ligne pour débuter l'entraînement.</p>
      )}

      <div style={{ marginTop: "1rem" }}>
        <span>
          Score : {session.correct} / {session.total}
        </span>{" "}
        {session.total > 0 && (
          <button type="button" onClick={() => void finishSession()}>
            Terminer la session
          </button>
        )}
      </div>

      <hr style={{ margin: "2rem 0" }} />

      <StatsDashboard repertoireId={repId} lineId={lineId} />
    </div>
  );
}
