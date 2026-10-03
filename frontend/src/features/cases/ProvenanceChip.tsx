interface Props {
  provenance?: string | null;
}

export function provenanceKind(provenance: string): "real" | "synthetic" {
  return provenance.toLowerCase().startsWith("synthetic") ? "synthetic" : "real";
}

export function ProvenanceChip({ provenance }: Props) {
  if (!provenance) return null;
  const kind = provenanceKind(provenance);
  return (
    <span className="chip chip--provenance" data-kind={kind} data-testid="provenance-chip">
      {provenance}
    </span>
  );
}
