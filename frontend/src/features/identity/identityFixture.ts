import type { Me } from "../../shared/types/contracts";

export function anonymousMe(): Me {
  return {
    principal: "caller://anonymous",
    kind: "anonymous",
    anonymous: true,
    scopes: ["cases:read", "recordings:read", "runs:create:live:curated", "runs:create:scripted", "runs:read"],
    key_id: null,
    expires_at: null,
    rate_limit: { limit: 120, remaining: 119, refill_per_s: 5 },
  };
}

export function namedMe(): Me {
  return {
    ...anonymousMe(),
    principal: "caller://ops",
    kind: "key",
    anonymous: false,
    scopes: [...anonymousMe().scopes, "uploads:write", "runs:create:live:upload", "audit:read"],
    key_id: "abc123",
    rate_limit: { limit: 400, remaining: 399, refill_per_s: 30 },
  };
}
