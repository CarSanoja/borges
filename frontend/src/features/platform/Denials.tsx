import { localDateTime } from "./localTime";

interface Denial {
  seq?: number | null;
  ts?: number | string | null;
  kind?: string | null;
  principal?: string | null;
  route?: string | null;
  reason?: string | null;
}

function when(ts: number | string | null | undefined): string {
  return localDateTime(ts) ?? "unknown";
}

export function denialsOf(facts: Record<string, unknown>): Denial[] {
  return Array.isArray(facts.recent_denials) ? (facts.recent_denials as Denial[]) : [];
}

export function Denials({ facts }: { facts: Record<string, unknown> }) {
  const rows = denialsOf(facts);
  if (rows.length === 0) return null;
  return (
    <div className="platform-denials" data-testid="recent-denials">
      <p className="platform-verify__label">Recent denials</p>
      <table>
        <thead>
          <tr>
            <th scope="col">Rule</th>
            <th scope="col">Agent</th>
            <th scope="col">Reason</th>
            <th scope="col">Time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={row.seq ?? index}>
              <td className="mono">{row.kind ?? "unknown"}</td>
              <td className="mono">{row.principal ?? "unknown"}</td>
              <td>{row.reason ?? row.route ?? "no reason recorded"}</td>
              <td className="mono">{when(row.ts)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
