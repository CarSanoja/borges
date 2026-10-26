import type { MemorySummary } from "../../shared/types/contracts";
import { KINDS, KIND_LABELS, shortFingerprint } from "./memoryFormat";
import { ForgetButton } from "./ForgetButton";

interface Props {
  summary: MemorySummary;
  canForget: boolean;
  onForget: (dataset?: string) => Promise<string | null>;
}

export function MemoryTable({ summary, canForget, onForget }: Props) {
  if (summary.datasets.length === 0) {
    return <p className="memory-empty">Nothing is remembered yet. Run a case with memory on and it appears here.</p>;
  }
  return (
    <table className="memory-table">
      <caption className="visually-hidden">Memories per dataset</caption>
      <thead>
        <tr>
          <th scope="col">Dataset</th>
          {KINDS.map((kind) => (
            <th scope="col" key={kind}>
              {KIND_LABELS[kind]}
            </th>
          ))}
          {canForget && <th scope="col">Erase</th>}
        </tr>
      </thead>
      <tbody>
        {summary.datasets.map((row) => (
          <tr key={row.dataset}>
            <th scope="row" title={row.dataset}>
              <span className="memory-dataset">{row.label ?? "Uploaded dataset"}</span>
              <span className="memory-fingerprint mono">{shortFingerprint(row.dataset)}</span>
            </th>
            {KINDS.map((kind) => (
              <td key={kind} className="mono">
                {row[kind]}
              </td>
            ))}
            {canForget && (
              <td>
                <ForgetButton label="Forget" onConfirm={() => onForget(row.dataset)} />
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
