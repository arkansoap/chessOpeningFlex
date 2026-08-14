import { useMemo, useState } from "react";
import type { RepertoireLine } from "../../types";

export interface RepertoireTreeProps {
  lines: RepertoireLine[];
  /** Selected line id. */
  selectedLineId?: string;
  onSelectLine?: (line: RepertoireLine) => void;
}

interface TreeNode {
  /** SAN move leading to this node (or "" for root). */
  move: string;
  line?: RepertoireLine;
  children: Map<string, TreeNode>;
}

/**
 * Builds a hierarchical tree of repertoire lines from their move sequences.
 * Lines that share a prefix are grouped under common nodes.
 */
export default function RepertoireTree({
  lines,
  selectedLineId,
  onSelectLine,
}: RepertoireTreeProps) {
  const root = useMemo(() => buildTree(lines), [lines]);

  return (
    <div className="repertoire-tree">
      {root.children.size === 0 ? (
        <p>Aucune ligne dans ce répertoire.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {Array.from(root.children.values()).map((node) => (
            <TreeBranch
              key={node.move}
              node={node}
              prefix={""}
              selectedLineId={selectedLineId}
              onSelectLine={onSelectLine}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function TreeBranch({
  node,
  prefix,
  selectedLineId,
  onSelectLine,
}: {
  node: TreeNode;
  prefix: string;
  selectedLineId?: string;
  onSelectLine?: (line: RepertoireLine) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children.size > 0;
  const label = prefix ? `${prefix} ${node.move}` : node.move;

  return (
    <li>
      <span
        onClick={() => hasChildren && setExpanded((e) => !e)}
        style={{ cursor: hasChildren ? "pointer" : "default", marginRight: 6 }}
      >
        {hasChildren ? (expanded ? "▼" : "▶") : "•"}
      </span>
      <span
        onClick={() => node.line && onSelectLine?.(node.line)}
        style={{
          cursor: node.line ? "pointer" : "default",
          fontWeight: node.line?.id === selectedLineId ? "bold" : "normal",
          background:
            node.line?.id === selectedLineId ? "#dbeafe" : "transparent",
          padding: "2px 6px",
          borderRadius: 4,
        }}
      >
        {label}
      </span>

      {expanded && hasChildren && (
        <ul style={{ listStyle: "none", paddingLeft: "1.25rem" }}>
          {Array.from(node.children.values()).map((child) => (
            <TreeBranch
              key={child.move}
              node={child}
              prefix={label}
              selectedLineId={selectedLineId}
              onSelectLine={onSelectLine}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function buildTree(lines: RepertoireLine[]): TreeNode {
  const root: TreeNode = { move: "", children: new Map() };
  for (const line of lines) {
    const moves = line.moves.split(" ").filter(Boolean);
    let current = root;
    for (const move of moves) {
      let child = current.children.get(move);
      if (!child) {
        child = { move, children: new Map() };
        current.children.set(move, child);
      }
      current = child;
    }
    // Attach the line to the last node (leaf).
    current.line = line;
  }
  return root;
}
