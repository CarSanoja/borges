import { useState } from "react";
import type { SpanNode } from "../../shared/types/contracts";
import { SpanDetails } from "./SpanDetails";
import { formatDuration, kindLabel } from "./spanFormat";

interface Props {
  node: SpanNode;
  depth: number;
  openDepth: number;
}

export function SpanRow({ node, depth, openDepth }: Props) {
  const [open, setOpen] = useState(depth < openDepth);
  const expandable = node.children.length > 0;
  const failed = node.status === "ERROR";
  return (
    <li className="trace-node" data-kind={node.kind ?? "span"} data-error={failed}>
      <div className="trace-row">
        {expandable ? (
          <button
            type="button"
            className="trace-toggle"
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} ${node.name}`}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? "−" : "+"}
          </button>
        ) : (
          <span className="trace-toggle trace-toggle--leaf" aria-hidden="true" />
        )}
        <span className="trace-kind">{kindLabel(node.kind)}</span>
        <span className="trace-name">{node.name}</span>
        {failed && <span className="trace-flag">error</span>}
        <span className="trace-duration mono">{formatDuration(node.duration_ms)}</span>
      </div>
      <SpanDetails node={node} />
      {expandable && open && (
        <ul className="trace-children">
          {node.children.map((child) => (
            <SpanRow key={child.span_id} node={child} depth={depth + 1} openDepth={openDepth} />
          ))}
        </ul>
      )}
    </li>
  );
}
