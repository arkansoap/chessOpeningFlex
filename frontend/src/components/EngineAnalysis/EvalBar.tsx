import { formatScore, scoreToWhiteShare } from "../../engine/uci";
import type { EngineLine } from "../../engine/types";

export interface EvalBarProps {
  /** Best line found so far; `null` renders a neutral bar. */
  line: EngineLine | null;
  /** Height in pixels; match the board for a clean alignment. */
  height?: number;
}

/**
 * Vertical evaluation bar, White at the bottom. Sits between the board and the
 * line list so the balance of the position is readable at a glance.
 */
export default function EvalBar({ line, height = 420 }: EvalBarProps) {
  const share = line ? scoreToWhiteShare(line) : 0.5;
  const label = line ? formatScore(line) : "—";
  const whiteAhead = share >= 0.5;

  return (
    <div
      className="eval-bar"
      style={{ height }}
      title={`Évaluation : ${label}`}
      role="img"
      aria-label={`Évaluation ${label} du point de vue des blancs`}
    >
      <div
        className="eval-bar__white"
        style={{ height: `${(share * 100).toFixed(1)}%` }}
      />
      <span
        className="eval-bar__label"
        style={{
          top: whiteAhead ? undefined : 4,
          bottom: whiteAhead ? 4 : undefined,
          color: whiteAhead ? "#111827" : "#f9fafb",
        }}
      >
        {label}
      </span>
    </div>
  );
}
