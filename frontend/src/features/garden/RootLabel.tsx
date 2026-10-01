import type { DatasetProfile } from "../../shared/types/contracts";
import { ROOT_RADIUS } from "./layout";

interface Props {
  dataset: DatasetProfile | undefined;
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

export function RootLabel({ dataset }: Props) {
  return (
    <g className="garden-core-label" aria-hidden="true">
      <text y={-ROOT_RADIUS - 24}>{truncate(dataset?.name ?? "dataset", 22)}</text>
      <text y={-ROOT_RADIUS - 10} className="mono">
        {dataset ? `${dataset.n_rows.toLocaleString("en-US")} rows` : ""}
      </text>
    </g>
  );
}
