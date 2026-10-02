import type { Me } from "../../shared/types/contracts";

const CAPABILITY_LABELS: ReadonlyArray<readonly [string, string]> = [
  ["cases:read", "browse cases"],
  ["recordings:read", "watch recordings"],
  ["runs:create:scripted", "start scripted runs"],
  ["runs:create:live:curated", "start live runs on curated cases"],
  ["runs:create:live:upload", "run uploaded datasets live"],
  ["uploads:write", "upload datasets"],
  ["registry:publish", "publish agent versions"],
  ["registry:approve", "approve agent versions"],
  ["audit:read", "read the audit log"],
  ["memory:write", "erase memories"],
];

export function capabilitySummary(me: Me): string[] {
  if (me.scopes.includes("admin")) return ["everything, as admin"];
  return CAPABILITY_LABELS.filter(([scope]) => me.scopes.includes(scope)).map(([, label]) => label);
}

export function principalLabel(me: Me): string {
  if (me.anonymous) return "Anonymous demo access";
  return me.principal.replace(/^caller:\/\//, "");
}

export function expiryLabel(expiresAt: number | null, now: number = Date.now()): string | null {
  if (expiresAt === null) return null;
  const seconds = Math.round(expiresAt - now / 1000);
  if (seconds <= 0) return "expired";
  if (seconds < 3600) return `expires in ${Math.ceil(seconds / 60)} min`;
  if (seconds < 172800) return `expires in ${Math.round(seconds / 3600)} h`;
  return `expires in ${Math.round(seconds / 86400)} days`;
}
