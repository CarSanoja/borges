import { describe, expect, it } from "vitest";
import { capabilitySummary, expiryLabel, principalLabel } from "./identityFormat";
import { anonymousMe, namedMe } from "./identityFixture";

describe("identity formatting", () => {
  it("names anonymous visitors and lists exactly the demo path", () => {
    expect(principalLabel(anonymousMe())).toBe("Anonymous demo access");
    expect(capabilitySummary(anonymousMe())).toEqual([
      "browse cases",
      "watch recordings",
      "start scripted runs",
      "start live runs on curated cases",
    ]);
  });

  it("names a key holder and lists the extra capabilities", () => {
    expect(principalLabel(namedMe())).toBe("ops");
    const summary = capabilitySummary(namedMe());
    expect(summary).toContain("upload datasets");
    expect(summary).toContain("read the audit log");
  });

  it("collapses admin to one line", () => {
    expect(capabilitySummary({ ...namedMe(), scopes: ["admin"] })).toEqual(["everything, as admin"]);
  });

  it("describes expiry", () => {
    const now = 1_000_000_000_000;
    expect(expiryLabel(null, now)).toBeNull();
    expect(expiryLabel(now / 1000 - 5, now)).toBe("expired");
    expect(expiryLabel(now / 1000 + 600, now)).toBe("expires in 10 min");
    expect(expiryLabel(now / 1000 + 7200, now)).toBe("expires in 2 h");
    expect(expiryLabel(now / 1000 + 86400 * 5, now)).toBe("expires in 5 days");
  });
});
