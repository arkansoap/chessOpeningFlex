import { useCallback, useEffect, useState } from "react";
import ChessBoard from "../ChessBoard/ChessBoard";
import { training as trainingApi } from "../../services/api";
import type { RepertoireLine, TrainingQuestion } from "../../types";

export interface TrainingModeProps {
  line: RepertoireLine;
  mode: "random" | "sequential" | "full_variation";
  /** Step counter for sequential mode (incremented on correct answers). */
  step?: number;
  onAnswer?: (correct: boolean) => void;
}

type Feedback = { kind: "ok" | "ko" | null; move: string };

/**
 * Training interface for a single line: fetches a question (a FEN position +
 * the expected SAN), accepts a drag-and-drop move, and shows immediate
 * feedback (correct / wrong).
 */
export default function TrainingMode({
  line,
  mode,
  step = 0,
  onAnswer,
}: TrainingModeProps) {
  const [question, setQuestion] = useState<TrainingQuestion | null>(null);
  const [feedback, setFeedback] = useState<Feedback>({ kind: null, move: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadQuestion = useCallback(async () => {
    setLoading(true);
    setFeedback({ kind: null, move: "" });
    setError(null);
    try {
      const q = await trainingApi.getQuestion({
        line_id: line.id,
        mode,
        step,
      });
      setQuestion(q);
    } catch (e: unknown) {
      setError(messageFromError(e));
      setQuestion(null);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [line.id, mode, step]);

  useEffect(() => {
    void loadQuestion();
  }, [loadQuestion]);

  const handleMove = useCallback(
    (san: string, fen: string): boolean | void => {
      if (!question) return;
      // validate against the backend
      void trainingApi
        .submitAnswer({
          line_id: line.id,
          move_played: san,
          expected_move: question.expected_move,
          fen,
        })
        .then((res) => {
          const correct = res.is_correct;
          setFeedback({ kind: correct ? "ok" : "ko", move: san });
          onAnswer?.(correct);
        })
        .catch(() => {
          setFeedback({ kind: "ko", move: san });
          onAnswer?.(false);
        });
      // accept the move locally; feedback will follow
      return true;
    },
    [question, line.id, onAnswer]
  );

  return (
    <div className="training-mode">
      <h3>Entraînement — {line.moves.split(" ").slice(0, 4).join(" ")}…</h3>
      {loading && <p>Chargement de la question…</p>}
      {error && <p style={{ color: "#dc2626" }}>Erreur : {error}</p>}

      {question && (
        <ChessBoard
          fen={question.fen}
          orientation={question.color_to_move}
          onMove={handleMove}
          highlightSquares={feedback.kind ? [question.fen.split(" ")[0]] : []}
        />
      )}

      {feedback.kind === "ok" && (
        <p style={{ color: "#16a34a" }}>✅ Correct : {feedback.move}</p>
      )}
      {feedback.kind === "ko" && question && (
        <p style={{ color: "#dc2626" }}>
          ❌ Faux : {feedback.move}. Attendu : {question.expected_move}
        </p>
      )}

      <button type="button" onClick={() => void loadQuestion()} style={{ marginTop: "1rem" }}>
        Question suivante
      </button>
    </div>
  );
}

function messageFromError(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const resp = (e as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail ?? "Impossible de charger la question.";
  }
  return "Impossible de charger la question.";
}
