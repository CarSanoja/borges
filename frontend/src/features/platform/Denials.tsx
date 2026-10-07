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
      <ul className="platform-denials__list">
        {rows.map((row, index) => (
          <li className="platform-denials__item" key={row.seq ?? index}>
            <span className="platform-denials__rule mono">{row.kind ?? "unknown"}</span>
            <span className="platform-denials__agent mono">{row.principal ?? "unknown"}</span>
            <span className="platform-denials__reason">{row.reason ?? row.route ?? "no reason recorded"}</span>
            <time className="platform-denials__time mono">{when(row.ts)}</time>
          </li>
        ))}
      </ul>
    </div>
  );
}
