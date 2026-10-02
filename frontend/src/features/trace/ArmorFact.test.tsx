import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AuditRecord } from "../../shared/types/contracts";
import { ArmorFact, armorLabel, isArmorRecord } from "./ArmorFact";

const RECORD: AuditRecord = {
  v: 1,
  seq: 7,
  ts: "2026-10-02T10:00:00Z",
  kind: "armor.screen",
  run_id: "r_1",
  trace_id: null,
  span_id: null,
  principal: "agent://borges/planner",
  decision: "deny",
  reason: "injection: override.ignore_rules",
  data: { action: "quarantine", field: "column_note:y" },
  prev_hash: "0".repeat(64),
  hash: "a".repeat(64),
};

describe("ArmorFact", () => {
  it("labels the action and the field and keeps the reason in the tooltip", () => {
    render(<ArmorFact record={RECORD} />);
    const code = screen.getByText("armor · quarantine · column_note:y");
    expect(code).toHaveAttribute("title", "injection: override.ignore_rules");
    expect(code.closest(".trace-fact")).toHaveAttribute("data-decision", "deny");
  });

  it("recognises armor records and falls back for scans", () => {
    expect(isArmorRecord(RECORD)).toBe(true);
    expect(isArmorRecord({ ...RECORD, kind: "model.call" })).toBe(false);
    expect(armorLabel({ ...RECORD, data: {} })).toBe("armor · scan");
  });
});
