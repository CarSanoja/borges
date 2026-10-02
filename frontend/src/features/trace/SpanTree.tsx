import type { SpanNode } from "../../shared/types/contracts";
import { SpanRow } from "./SpanRow";

interface Props {
  roots: SpanNode[];
  openDepth?: number;
}

export function SpanTree({ roots, openDepth = 2 }: Props) {
  return (
    <ul className="trace-tree" aria-label="Span tree">
      {roots.map((root) => (
        <SpanRow key={root.span_id} node={root} depth={0} openDepth={openDepth} />
      ))}
    </ul>
  );
}
