import type { AuditRecord } from "../../shared/types/contracts";

export const ARMOR_KINDS = ["armor.screen", "armor.upload_scan"];

export function isArmorRecord(record: AuditRecord): boolean {
  return ARMOR_KINDS.includes(record.kind);
}

export function armorLabel(record: AuditRecord): string {
  const action = typeof record.data.action === "string" ? record.data.action : "scan";
  const field = typeof record.data.field === "string" ? record.data.field : null;
  return field ? `armor · ${action} · ${field}` : `armor · ${action}`;
}

export function ArmorFact({ record }: { record: AuditRecord }) {
  return (
    <span className="trace-fact trace-fact--armor" data-decision={record.decision ?? "none"}>
      <span className="trace-fact__label">audit #{record.seq}</span>
      <code className="mono" title={record.reason ?? record.hash}>
        {armorLabel(record)}
      </code>
    </span>
  );
}
