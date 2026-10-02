import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChainBadge, chainState } from "./ChainBadge";
import { CHAIN_OK } from "./traceFixture";

describe("ChainBadge", () => {
  it("shows a verified chain with its record count", () => {
    render(<ChainBadge chain={CHAIN_OK} />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveAttribute("data-state", "verified");
    expect(badge).toHaveTextContent("Audit chain verified · 9 records");
  });

  it("shows a broken chain with the first broken record", () => {
    render(<ChainBadge chain={{ ...CHAIN_OK, ok: false, broken_seq: 3, reason: "hash mismatch" }} />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveAttribute("data-state", "broken");
    expect(badge).toHaveTextContent("broken at record 3");
    expect(badge).toHaveAttribute("title", "hash mismatch");
  });

  it("reports no chain for missing or empty logs", () => {
    expect(chainState(null)).toBe("none");
    expect(chainState({ ...CHAIN_OK, exists: false })).toBe("none");
    expect(chainState({ ...CHAIN_OK, records: 0 })).toBe("none");
  });
});
