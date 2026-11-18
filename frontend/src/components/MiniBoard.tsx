import { useMemo } from "react";
import { positionOf } from "../lib/chess";

const GLYPHS: Record<string, string> = {
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
};

export interface MiniBoardProps {
  /** Moves from the start leading to the position. */
  line?: string[];
  /** Or the position itself. */
  fen?: string;
  orientation?: "white" | "black";
  /** Squares to mark, e.g. the move being discussed. */
  highlight?: string[];
}

/**
 * Small static diagram for lists. Drawn with text glyphs: dozens of them on a
 * page stay cheap, unlike full interactive boards.
 */
export default function MiniBoard({ line, fen, orientation = "white", highlight = [] }: MiniBoardProps) {
  const placement = useMemo(
    () => (fen ?? positionOf(line ?? []).fen).split(" ")[0],
    [fen, line]
  );

  const squares: { name: string; piece: string | null }[] = [];
  placement.split("/").forEach((row, rowIndex) => {
    let file = 0;
    for (const char of row) {
      if (/\d/.test(char)) {
        for (let i = 0; i < Number(char); i++) {
          squares.push({ name: `${"abcdefgh"[file]}${8 - rowIndex}`, piece: null });
          file += 1;
        }
      } else {
        squares.push({ name: `${"abcdefgh"[file]}${8 - rowIndex}`, piece: char });
        file += 1;
      }
    }
  });
  if (orientation === "black") squares.reverse();

  return (
    <div className="miniboard" aria-hidden="true">
      {squares.map(({ name, piece }) => {
        const dark = (name.charCodeAt(0) + Number(name[1])) % 2 === 0;
        const classes = [
          "miniboard__square",
          dark ? "miniboard__square--dark" : "",
          highlight.includes(name) ? "miniboard__square--marked" : "",
        ];
        return (
          <span key={name} className={classes.join(" ")}>
            {piece && (
              <span className={piece === piece.toUpperCase() ? "miniboard__white" : "miniboard__black"}>
                {GLYPHS[piece.toLowerCase()]}
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}
