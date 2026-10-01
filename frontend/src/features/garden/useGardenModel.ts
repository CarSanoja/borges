import { useMemo } from "react";
import type { RunSnapshot, Universe } from "../../shared/types/contracts";
import { universeTone } from "./colors";
import type { Tone } from "./colors";
import type { LinkRole } from "./GardenLink";
import { computeLayout } from "./layout";
import type { GardenLayout, GardenLayoutNode } from "./layout";

export interface GardenLinkSpec {
  id: string;
  parent: GardenLayoutNode;
  child: GardenLayoutNode;
  role: LinkRole;
}

export interface GardenModel {
  layout: GardenLayout;
  byId: Map<string, GardenLayoutNode>;
  leafUniverse: Map<string, Universe>;
  leafTone: Map<string, Tone>;
  links: GardenLinkSpec[];
}

const ROLE_ORDER: Record<LinkRole, number> = { plain: 0, baseline: 1, flip: 2, selected: 3 };

function checkpointsOf(universes: Record<string, Universe>, id: string | null | undefined): Set<string> {
  return new Set(id ? (universes[id]?.checkpoints ?? []) : []);
}

export function useGardenModel(snapshot: RunSnapshot, selectedUniverseId: string | null): GardenModel {
  const { checkpoints, plan, garden, flip } = snapshot;
  const stepCount = plan?.steps.length ?? 0;
  const layout = useMemo(() => computeLayout(checkpoints, stepCount), [checkpoints, stepCount]);

  const leafMaps = useMemo(() => {
    const leafUniverse = new Map<string, Universe>();
    const leafTone = new Map<string, Tone>();
    const ordered = Object.values(garden.universes).sort(
      (a, b) => Number(a.id === flip?.universe_id) - Number(b.id === flip?.universe_id),
    );
    for (const universe of ordered) {
      const last = universe.checkpoints[universe.checkpoints.length - 1];
      if (!last) continue;
      leafUniverse.set(last, universe);
      leafTone.set(last, universeTone(universe, garden.baseline_id));
    }
    return { leafUniverse, leafTone };
  }, [garden, flip?.universe_id]);

  const byId = useMemo(() => new Map(layout.nodes.map((n) => [n.id, n])), [layout]);

  const links = useMemo(() => {
    const baseline = checkpointsOf(garden.universes, garden.baseline_id);
    const flipped = checkpointsOf(garden.universes, flip?.universe_id);
    const selected = checkpointsOf(garden.universes, selectedUniverseId);
    const out: GardenLinkSpec[] = [];
    for (const child of layout.nodes) {
      const parent = child.parentId ? byId.get(child.parentId) : undefined;
      if (!parent) continue;
      const role: LinkRole = selected.has(child.id)
        ? "selected"
        : flipped.has(child.id)
          ? "flip"
          : baseline.has(child.id)
            ? "baseline"
            : "plain";
      out.push({ id: child.id, parent, child, role });
    }
    return out.sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role]);
  }, [layout, byId, garden, flip?.universe_id, selectedUniverseId]);

  return { layout, byId, links, ...leafMaps };
}
